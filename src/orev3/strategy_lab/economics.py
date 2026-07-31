"""Immutable RFC-011 Phase 1 economic scenario and participant state."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


SQUARE_COUNT = 25
ECONOMIC_SCENARIO_SCHEMA_VERSION = 1


class LamportApportionmentRule(str, Enum):
    """Canonical rule selected for later integer budget apportionment."""

    LARGEST_REMAINDER_CANDIDATE_ORDER_V1 = (
        "largest_remainder_candidate_order_v1"
    )


class MissingOutcomePolicy(str, Enum):
    """Fail-closed policy for unavailable finalized replay outcomes."""

    FAIL_CLOSED = "fail_closed"


class CheckpointState(str, Enum):
    """Structural checkpoint status held by participant economic state."""

    NOT_REQUIRED = "not_required"
    REQUIRED = "required"
    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class CapitalReserveRules:
    """Lamport reserves excluded from a participant's deployment budget."""

    minimum_liquid_reserve_lamports: int
    transaction_cost_reserve_lamports: int
    checkpoint_cost_reserve_lamports: int

    def __post_init__(self) -> None:
        _validate_nonnegative_integer(
            "minimum_liquid_reserve_lamports",
            self.minimum_liquid_reserve_lamports,
        )
        _validate_nonnegative_integer(
            "transaction_cost_reserve_lamports",
            self.transaction_cost_reserve_lamports,
        )
        _validate_nonnegative_integer(
            "checkpoint_cost_reserve_lamports",
            self.checkpoint_cost_reserve_lamports,
        )

    @property
    def total_reserved_lamports(self) -> int:
        """Return the deterministic sum of all configured reserves."""

        return (
            self.minimum_liquid_reserve_lamports
            + self.transaction_cost_reserve_lamports
            + self.checkpoint_cost_reserve_lamports
        )


@dataclass(frozen=True, slots=True)
class BudgetModel:
    """Immutable SOL budget and reserve configuration."""

    participant_initial_sol_balance_lamports: int
    per_round_deployment_budget_lamports: int
    capital_reserve_rules: CapitalReserveRules

    def __post_init__(self) -> None:
        _validate_nonnegative_integer(
            "participant_initial_sol_balance_lamports",
            self.participant_initial_sol_balance_lamports,
        )
        _validate_nonnegative_integer(
            "per_round_deployment_budget_lamports",
            self.per_round_deployment_budget_lamports,
        )
        if not isinstance(
            self.capital_reserve_rules,
            CapitalReserveRules,
        ):
            raise TypeError(
                "capital_reserve_rules must be CapitalReserveRules"
            )
        required = (
            self.per_round_deployment_budget_lamports
            + self.capital_reserve_rules.total_reserved_lamports
        )
        if required > self.participant_initial_sol_balance_lamports:
            raise ValueError(
                "initial SOL balance must cover the per-round deployment "
                "budget and all capital reserves"
            )

    @property
    def maximum_initial_deployable_lamports(self) -> int:
        """Return initial SOL remaining after all configured reserves."""

        return (
            self.participant_initial_sol_balance_lamports
            - self.capital_reserve_rules.total_reserved_lamports
        )


@dataclass(frozen=True, slots=True)
class FeeAssumptions:
    """Immutable offline assumptions for Solana transaction costs."""

    base_transaction_fee_lamports: int
    priority_fee_lamports: int
    failed_transaction_fee_lamports: int
    checkpoint_transaction_fee_lamports: int

    def __post_init__(self) -> None:
        for name, value in (
            (
                "base_transaction_fee_lamports",
                self.base_transaction_fee_lamports,
            ),
            (
                "priority_fee_lamports",
                self.priority_fee_lamports,
            ),
            (
                "failed_transaction_fee_lamports",
                self.failed_transaction_fee_lamports,
            ),
            (
                "checkpoint_transaction_fee_lamports",
                self.checkpoint_transaction_fee_lamports,
            ),
        ):
            _validate_nonnegative_integer(name, value)

    @property
    def included_transaction_fee_lamports(self) -> int:
        """Return the assumed fee for one included deployment transaction."""

        return (
            self.base_transaction_fee_lamports
            + self.priority_fee_lamports
        )


@dataclass(frozen=True, slots=True)
class CheckpointAssumptions:
    """Immutable assumptions governing checkpoint eligibility and reserve."""

    required_before_next_round: bool
    protocol_checkpoint_reserve_lamports: int

    def __post_init__(self) -> None:
        if not isinstance(self.required_before_next_round, bool):
            raise TypeError(
                "required_before_next_round must be a boolean"
            )
        _validate_nonnegative_integer(
            "protocol_checkpoint_reserve_lamports",
            self.protocol_checkpoint_reserve_lamports,
        )


@dataclass(frozen=True, slots=True)
class TransactionAssumptions:
    """Immutable offline transaction and inclusion assumptions."""

    maximum_transaction_size_bytes: int
    compute_unit_limit: int
    maximum_instructions_per_transaction: int
    inclusion_latency_slots: int
    transaction_base_size_bytes: int
    deploy_instruction_size_bytes: int
    transaction_base_compute_units: int
    deploy_instruction_compute_units: int
    maximum_transactions_per_slot: int
    submission_delay_slots: int

    def __post_init__(self) -> None:
        _validate_positive_integer(
            "maximum_transaction_size_bytes",
            self.maximum_transaction_size_bytes,
        )
        _validate_positive_integer(
            "compute_unit_limit",
            self.compute_unit_limit,
        )
        _validate_positive_integer(
            "maximum_instructions_per_transaction",
            self.maximum_instructions_per_transaction,
        )
        _validate_nonnegative_integer(
            "inclusion_latency_slots",
            self.inclusion_latency_slots,
        )
        _validate_nonnegative_integer(
            "transaction_base_size_bytes",
            self.transaction_base_size_bytes,
        )
        _validate_positive_integer(
            "deploy_instruction_size_bytes",
            self.deploy_instruction_size_bytes,
        )
        _validate_nonnegative_integer(
            "transaction_base_compute_units",
            self.transaction_base_compute_units,
        )
        _validate_positive_integer(
            "deploy_instruction_compute_units",
            self.deploy_instruction_compute_units,
        )
        _validate_positive_integer(
            "maximum_transactions_per_slot",
            self.maximum_transactions_per_slot,
        )
        _validate_nonnegative_integer(
            "submission_delay_slots",
            self.submission_delay_slots,
        )


@dataclass(frozen=True, slots=True)
class OutcomePolicy:
    """Immutable finalized-outcome provenance and continuity policy."""

    accepted_sources: tuple[str, ...]
    missing_outcome_policy: MissingOutcomePolicy
    require_contiguous_outcomes: bool

    def __post_init__(self) -> None:
        sources = tuple(self.accepted_sources)
        if not sources:
            raise ValueError("accepted_sources must not be empty")
        if len(set(sources)) != len(sources):
            raise ValueError("accepted_sources must be unique")
        canonical_sources = ("observed", "enriched")
        if any(source not in canonical_sources for source in sources):
            raise ValueError(
                "accepted_sources may contain only observed and enriched"
            )
        ordered_sources = tuple(
            source
            for source in canonical_sources
            if source in sources
        )
        object.__setattr__(self, "accepted_sources", ordered_sources)
        if not isinstance(
            self.missing_outcome_policy,
            MissingOutcomePolicy,
        ):
            raise TypeError(
                "missing_outcome_policy must be MissingOutcomePolicy"
            )
        if not isinstance(self.require_contiguous_outcomes, bool):
            raise TypeError(
                "require_contiguous_outcomes must be a boolean"
            )


@dataclass(frozen=True, slots=True)
class ComponentIdentities:
    """Immutable identities for every deterministic RFC-011 component."""

    allocation_materializer: str
    protocol_constraint_model: str
    transaction_model: str
    inclusion_model: str
    settlement_model: str
    simulation_runner: str
    metrics_engine: str

    def __post_init__(self) -> None:
        for name, value in self.as_mapping().items():
            _validate_canonical_identity(name, value)

    def as_mapping(self) -> dict[str, str]:
        """Return a fresh canonical mapping used by scenario identity."""

        return {
            "allocation_materializer": self.allocation_materializer,
            "inclusion_model": self.inclusion_model,
            "metrics_engine": self.metrics_engine,
            "protocol_constraint_model": self.protocol_constraint_model,
            "settlement_model": self.settlement_model,
            "simulation_runner": self.simulation_runner,
            "transaction_model": self.transaction_model,
        }


@dataclass(frozen=True, slots=True)
class ParticipantEconomicState:
    """Immutable protocol-native resource state for one ORE authority."""

    available_sol_lamports: int
    accrued_sol_lamports: int
    accrued_ore: int
    deployed_lamports: tuple[int, ...]
    checkpoint_state: CheckpointState
    cumulative_protocol_costs_lamports: int
    cumulative_transaction_costs_lamports: int
    current_round: int | None
    last_economically_settled_round: int | None
    occupied_squares: tuple[bool, ...] = field(init=False)
    state_identity: str = field(init=False)

    def __post_init__(self) -> None:
        for name, value in (
            ("available_sol_lamports", self.available_sol_lamports),
            ("accrued_sol_lamports", self.accrued_sol_lamports),
            ("accrued_ore", self.accrued_ore),
            (
                "cumulative_protocol_costs_lamports",
                self.cumulative_protocol_costs_lamports,
            ),
            (
                "cumulative_transaction_costs_lamports",
                self.cumulative_transaction_costs_lamports,
            ),
        ):
            _validate_nonnegative_integer(name, value)

        deployed = tuple(self.deployed_lamports)
        if len(deployed) != SQUARE_COUNT:
            raise ValueError(
                "deployed_lamports must contain exactly 25 values"
            )
        for value in deployed:
            _validate_nonnegative_integer(
                "deployed_lamports value",
                value,
            )
        object.__setattr__(self, "deployed_lamports", deployed)
        object.__setattr__(
            self,
            "occupied_squares",
            tuple(value > 0 for value in deployed),
        )

        if not isinstance(self.checkpoint_state, CheckpointState):
            raise TypeError(
                "checkpoint_state must be CheckpointState"
            )
        _validate_optional_nonnegative_integer(
            "current_round",
            self.current_round,
        )
        _validate_optional_nonnegative_integer(
            "last_economically_settled_round",
            self.last_economically_settled_round,
        )
        if self.current_round is None and any(deployed):
            raise ValueError(
                "a positive deployment requires current_round"
            )
        if (
            self.current_round is not None
            and self.last_economically_settled_round is not None
            and self.last_economically_settled_round > self.current_round
        ):
            raise ValueError(
                "last economically settled round cannot follow current_round"
            )

        object.__setattr__(
            self,
            "state_identity",
            _canonical_sha256_identity(
                "rfc011-participant-state-sha256",
                self._identity_payload(),
            ),
        )

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "accrued_ore": self.accrued_ore,
            "accrued_sol_lamports": self.accrued_sol_lamports,
            "available_sol_lamports": self.available_sol_lamports,
            "checkpoint_state": self.checkpoint_state.value,
            "cumulative_protocol_costs_lamports": (
                self.cumulative_protocol_costs_lamports
            ),
            "cumulative_transaction_costs_lamports": (
                self.cumulative_transaction_costs_lamports
            ),
            "current_round": self.current_round,
            "deployed_lamports": list(self.deployed_lamports),
            "last_economically_settled_round": (
                self.last_economically_settled_round
            ),
            "occupied_squares": list(self.occupied_squares),
        }


@dataclass(frozen=True, slots=True)
class EconomicScenario:
    """Immutable configuration and identity for one RFC-011 simulation."""

    protocol_revision: str
    budget: BudgetModel
    lamport_apportionment_rule: LamportApportionmentRule
    fee_assumptions: FeeAssumptions
    checkpoint_assumptions: CheckpointAssumptions
    transaction_assumptions: TransactionAssumptions
    outcome_policy: OutcomePolicy
    replay_identity: str
    dataset_identity: str
    component_identities: ComponentIdentities
    schema_version: int = ECONOMIC_SCENARIO_SCHEMA_VERSION
    scenario_identity: str = field(init=False)

    def __post_init__(self) -> None:
        if self.schema_version != ECONOMIC_SCENARIO_SCHEMA_VERSION:
            raise ValueError(
                "schema_version must equal "
                f"{ECONOMIC_SCENARIO_SCHEMA_VERSION}"
            )
        _validate_canonical_identity(
            "protocol_revision",
            self.protocol_revision,
        )
        _validate_canonical_identity(
            "replay_identity",
            self.replay_identity,
        )
        _validate_canonical_identity(
            "dataset_identity",
            self.dataset_identity,
        )
        for name, value, expected in (
            ("budget", self.budget, BudgetModel),
            (
                "lamport_apportionment_rule",
                self.lamport_apportionment_rule,
                LamportApportionmentRule,
            ),
            (
                "fee_assumptions",
                self.fee_assumptions,
                FeeAssumptions,
            ),
            (
                "checkpoint_assumptions",
                self.checkpoint_assumptions,
                CheckpointAssumptions,
            ),
            (
                "transaction_assumptions",
                self.transaction_assumptions,
                TransactionAssumptions,
            ),
            (
                "outcome_policy",
                self.outcome_policy,
                OutcomePolicy,
            ),
            (
                "component_identities",
                self.component_identities,
                ComponentIdentities,
            ),
        ):
            if not isinstance(value, expected):
                raise TypeError(
                    f"{name} must be {expected.__name__}"
                )

        reserves = self.budget.capital_reserve_rules
        minimum_transaction_reserve = (
            self.fee_assumptions.included_transaction_fee_lamports
        )
        if (
            reserves.transaction_cost_reserve_lamports
            < minimum_transaction_reserve
        ):
            raise ValueError(
                "transaction cost reserve must cover at least one included "
                "transaction fee"
            )
        minimum_checkpoint_reserve = (
            self.checkpoint_assumptions
            .protocol_checkpoint_reserve_lamports
            + self.fee_assumptions
            .checkpoint_transaction_fee_lamports
        )
        if (
            reserves.checkpoint_cost_reserve_lamports
            < minimum_checkpoint_reserve
        ):
            raise ValueError(
                "checkpoint cost reserve must cover protocol and "
                "transaction checkpoint costs"
            )

        object.__setattr__(
            self,
            "scenario_identity",
            _canonical_sha256_identity(
                "rfc011-economic-scenario-sha256",
                self._identity_payload(),
            ),
        )

    @property
    def participant_initial_sol_balance_lamports(self) -> int:
        return self.budget.participant_initial_sol_balance_lamports

    @property
    def per_round_deployment_budget_lamports(self) -> int:
        return self.budget.per_round_deployment_budget_lamports

    @property
    def capital_reserve_rules(self) -> CapitalReserveRules:
        return self.budget.capital_reserve_rules

    def _identity_payload(self) -> dict[str, Any]:
        reserves = self.capital_reserve_rules
        fees = self.fee_assumptions
        checkpoint = self.checkpoint_assumptions
        transaction = self.transaction_assumptions
        policy = self.outcome_policy
        return {
            "budget": {
                "capital_reserve_rules": {
                    "checkpoint_cost_reserve_lamports": (
                        reserves.checkpoint_cost_reserve_lamports
                    ),
                    "minimum_liquid_reserve_lamports": (
                        reserves.minimum_liquid_reserve_lamports
                    ),
                    "transaction_cost_reserve_lamports": (
                        reserves.transaction_cost_reserve_lamports
                    ),
                },
                "participant_initial_sol_balance_lamports": (
                    self.participant_initial_sol_balance_lamports
                ),
                "per_round_deployment_budget_lamports": (
                    self.per_round_deployment_budget_lamports
                ),
            },
            "checkpoint_assumptions": {
                "protocol_checkpoint_reserve_lamports": (
                    checkpoint.protocol_checkpoint_reserve_lamports
                ),
                "required_before_next_round": (
                    checkpoint.required_before_next_round
                ),
            },
            "component_identities": (
                self.component_identities.as_mapping()
            ),
            "dataset_identity": self.dataset_identity,
            "fee_assumptions": {
                "base_transaction_fee_lamports": (
                    fees.base_transaction_fee_lamports
                ),
                "checkpoint_transaction_fee_lamports": (
                    fees.checkpoint_transaction_fee_lamports
                ),
                "failed_transaction_fee_lamports": (
                    fees.failed_transaction_fee_lamports
                ),
                "priority_fee_lamports": (
                    fees.priority_fee_lamports
                ),
            },
            "lamport_apportionment_rule": (
                self.lamport_apportionment_rule.value
            ),
            "outcome_policy": {
                "accepted_sources": list(policy.accepted_sources),
                "missing_outcome_policy": (
                    policy.missing_outcome_policy.value
                ),
                "require_contiguous_outcomes": (
                    policy.require_contiguous_outcomes
                ),
            },
            "protocol_revision": self.protocol_revision,
            "replay_identity": self.replay_identity,
            "schema_version": self.schema_version,
            "transaction_assumptions": {
                "compute_unit_limit": transaction.compute_unit_limit,
                "deploy_instruction_compute_units": (
                    transaction.deploy_instruction_compute_units
                ),
                "deploy_instruction_size_bytes": (
                    transaction.deploy_instruction_size_bytes
                ),
                "inclusion_latency_slots": (
                    transaction.inclusion_latency_slots
                ),
                "maximum_instructions_per_transaction": (
                    transaction.maximum_instructions_per_transaction
                ),
                "maximum_transactions_per_slot": (
                    transaction.maximum_transactions_per_slot
                ),
                "maximum_transaction_size_bytes": (
                    transaction.maximum_transaction_size_bytes
                ),
                "submission_delay_slots": (
                    transaction.submission_delay_slots
                ),
                "transaction_base_compute_units": (
                    transaction.transaction_base_compute_units
                ),
                "transaction_base_size_bytes": (
                    transaction.transaction_base_size_bytes
                ),
            },
        }


def _validate_nonnegative_integer(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")


def _validate_positive_integer(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")


def _validate_optional_nonnegative_integer(
    name: str,
    value: object,
) -> None:
    if value is not None:
        _validate_nonnegative_integer(name, value)


def _validate_canonical_identity(name: str, value: object) -> None:
    if (
        not isinstance(value, str)
        or not value
        or value.strip() != value
    ):
        raise ValueError(
            f"{name} must be a nonempty canonical string"
        )


def _canonical_sha256_identity(
    prefix: str,
    payload: dict[str, Any],
) -> str:
    canonical = json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(canonical).hexdigest()}"


__all__ = (
    "BudgetModel",
    "CapitalReserveRules",
    "CheckpointAssumptions",
    "CheckpointState",
    "ComponentIdentities",
    "ECONOMIC_SCENARIO_SCHEMA_VERSION",
    "EconomicScenario",
    "FeeAssumptions",
    "LamportApportionmentRule",
    "MissingOutcomePolicy",
    "OutcomePolicy",
    "ParticipantEconomicState",
    "SQUARE_COUNT",
    "TransactionAssumptions",
)
