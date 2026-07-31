"""Deterministic offline RFC-011 Phase 4 transaction modeling."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from orev3.strategy_lab.constraints import ProtocolDeploymentPlan
from orev3.strategy_lab.economics import EconomicScenario


class TransactionViolationCode(str, Enum):
    """Stable reasons that a modeled deployment was not included."""

    PROTOCOL_REVISION_MISMATCH = "protocol_revision_mismatch"
    SCENARIO_IDENTITY_MISMATCH = "scenario_identity_mismatch"
    TRANSACTION_MODEL_IDENTITY_MISMATCH = (
        "transaction_model_identity_mismatch"
    )
    INCLUSION_MODEL_IDENTITY_MISMATCH = "inclusion_model_identity_mismatch"
    TRANSACTION_BASE_SIZE_EXCEEDED = "transaction_base_size_exceeded"
    TRANSACTION_BASE_COMPUTE_EXCEEDED = (
        "transaction_base_compute_exceeded"
    )
    INSTRUCTION_SIZE_EXCEEDED = "instruction_size_exceeded"
    INSTRUCTION_COMPUTE_EXCEEDED = "instruction_compute_exceeded"
    TRANSACTION_COST_RESERVE_EXCEEDED = (
        "transaction_cost_reserve_exceeded"
    )
    ROUND_DEADLINE_REACHED = "round_deadline_reached"


class TransactionInclusionStatus(str, Enum):
    """The deterministic modeled inclusion outcome."""

    INCLUDED = "included"
    UNINCLUDED = "unincluded"


@dataclass(frozen=True, slots=True)
class TransactionViolation:
    """One immutable transaction-feasibility or inclusion failure."""

    code: TransactionViolationCode
    message: str
    instruction_identifiers: tuple[str, ...] = ()
    transaction_sequence_numbers: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.code, TransactionViolationCode):
            raise TypeError("code must be a TransactionViolationCode")
        _validate_canonical_string("message", self.message)
        instructions = tuple(self.instruction_identifiers)
        if len(set(instructions)) != len(instructions):
            raise ValueError("instruction identifiers must be unique")
        for value in instructions:
            _validate_canonical_string("instruction identifier", value)
        transactions = tuple(self.transaction_sequence_numbers)
        if any(
            isinstance(value, bool)
            or not isinstance(value, int)
            or value <= 0
            for value in transactions
        ):
            raise ValueError(
                "transaction sequence numbers must be positive integers"
            )
        if tuple(sorted(set(transactions))) != transactions:
            raise ValueError(
                "transaction sequence numbers must be unique and ascending"
            )
        object.__setattr__(self, "instruction_identifiers", instructions)
        object.__setattr__(
            self,
            "transaction_sequence_numbers",
            transactions,
        )


@dataclass(frozen=True, slots=True)
class DeployInstruction:
    """One modeled ORE Deploy instruction, not a Solana transaction."""

    amount_lamports: int
    square_identifiers: tuple[int, ...]
    square_mask: int
    assumed_size_bytes: int
    assumed_compute_units: int
    instruction_identity: str = field(init=False)

    def __post_init__(self) -> None:
        _validate_positive_integer("amount_lamports", self.amount_lamports)
        squares = tuple(self.square_identifiers)
        if not squares:
            raise ValueError("a Deploy instruction must select a square")
        if any(
            isinstance(square, bool)
            or not isinstance(square, int)
            or not 0 <= square < 25
            for square in squares
        ):
            raise ValueError("square identifiers must be in 0..24")
        if tuple(sorted(set(squares))) != squares:
            raise ValueError("square identifiers must be unique and ascending")
        expected_mask = sum(1 << square for square in squares)
        if self.square_mask != expected_mask:
            raise ValueError("square_mask does not match square identifiers")
        _validate_positive_integer(
            "assumed_size_bytes",
            self.assumed_size_bytes,
        )
        _validate_positive_integer(
            "assumed_compute_units",
            self.assumed_compute_units,
        )
        object.__setattr__(self, "square_identifiers", squares)
        object.__setattr__(
            self,
            "instruction_identity",
            _identity(
                "rfc011-deploy-instruction-sha256",
                {
                    "amount_lamports": self.amount_lamports,
                    "assumed_compute_units": self.assumed_compute_units,
                    "assumed_size_bytes": self.assumed_size_bytes,
                    "square_identifiers": list(squares),
                    "square_mask": self.square_mask,
                },
            ),
        )


@dataclass(frozen=True, slots=True)
class PlannedTransaction:
    """One deterministic group of modeled Deploy instructions."""

    sequence_number: int
    instructions: tuple[DeployInstruction, ...]
    assumed_size_bytes: int
    assumed_compute_units: int
    assumed_submission_slot: int
    assumed_inclusion_slot: int
    transaction_identity: str = field(init=False)

    def __post_init__(self) -> None:
        _validate_positive_integer("sequence_number", self.sequence_number)
        instructions = tuple(self.instructions)
        if not instructions or not all(
            isinstance(value, DeployInstruction) for value in instructions
        ):
            raise ValueError(
                "instructions must contain DeployInstruction values"
            )
        _validate_nonnegative_integer(
            "assumed_size_bytes",
            self.assumed_size_bytes,
        )
        _validate_nonnegative_integer(
            "assumed_compute_units",
            self.assumed_compute_units,
        )
        _validate_nonnegative_integer(
            "assumed_submission_slot",
            self.assumed_submission_slot,
        )
        _validate_nonnegative_integer(
            "assumed_inclusion_slot",
            self.assumed_inclusion_slot,
        )
        if self.assumed_inclusion_slot < self.assumed_submission_slot:
            raise ValueError("inclusion slot cannot precede submission slot")
        object.__setattr__(self, "instructions", instructions)
        object.__setattr__(
            self,
            "transaction_identity",
            _identity(
                "rfc011-planned-transaction-sha256",
                {
                    "assumed_compute_units": self.assumed_compute_units,
                    "assumed_inclusion_slot": self.assumed_inclusion_slot,
                    "assumed_size_bytes": self.assumed_size_bytes,
                    "assumed_submission_slot": self.assumed_submission_slot,
                    "instruction_identities": [
                        value.instruction_identity for value in instructions
                    ],
                    "sequence_number": self.sequence_number,
                },
            ),
        )


@dataclass(frozen=True, slots=True)
class TransactionPlan:
    """Immutable offline action plan derived from a protocol deployment."""

    protocol_deployment_plan_identity: str
    scenario_identity: str
    transaction_model_identity: str
    round_identifier: int
    decision_slot: int
    instructions: tuple[DeployInstruction, ...]
    transactions: tuple[PlannedTransaction, ...]
    planned_transaction_fees_lamports: int
    planned_priority_fees_lamports: int
    violations: tuple[TransactionViolation, ...] = ()
    transaction_plan_identity: str = field(init=False)

    def __post_init__(self) -> None:
        for name, value in (
            (
                "protocol_deployment_plan_identity",
                self.protocol_deployment_plan_identity,
            ),
            ("scenario_identity", self.scenario_identity),
            ("transaction_model_identity", self.transaction_model_identity),
        ):
            _validate_canonical_string(name, value)
        _validate_nonnegative_integer("round_identifier", self.round_identifier)
        _validate_nonnegative_integer("decision_slot", self.decision_slot)
        instructions = tuple(self.instructions)
        transactions = tuple(self.transactions)
        violations = tuple(self.violations)
        if not all(isinstance(value, DeployInstruction) for value in instructions):
            raise TypeError("instructions must contain DeployInstruction values")
        if not all(isinstance(value, PlannedTransaction) for value in transactions):
            raise TypeError("transactions must contain PlannedTransaction values")
        if not all(isinstance(value, TransactionViolation) for value in violations):
            raise TypeError("violations must contain TransactionViolation values")
        if len({value.code for value in violations}) != len(violations):
            raise ValueError("transaction violation codes must be unique")
        if tuple(value.sequence_number for value in transactions) != tuple(
            range(1, len(transactions) + 1)
        ):
            raise ValueError("transaction sequence must be contiguous from one")
        flattened = tuple(
            instruction
            for transaction in transactions
            for instruction in transaction.instructions
        )
        if transactions and flattened != instructions:
            raise ValueError("transaction grouping must preserve instruction order")
        if violations and transactions and any(
            value.code
            in {
                TransactionViolationCode.INSTRUCTION_SIZE_EXCEEDED,
                TransactionViolationCode.INSTRUCTION_COMPUTE_EXCEEDED,
                TransactionViolationCode.TRANSACTION_BASE_SIZE_EXCEEDED,
                TransactionViolationCode.TRANSACTION_BASE_COMPUTE_EXCEEDED,
            }
            for value in violations
        ):
            raise ValueError("intrinsically infeasible plans cannot be grouped")
        _validate_nonnegative_integer(
            "planned_transaction_fees_lamports",
            self.planned_transaction_fees_lamports,
        )
        _validate_nonnegative_integer(
            "planned_priority_fees_lamports",
            self.planned_priority_fees_lamports,
        )
        object.__setattr__(self, "instructions", instructions)
        object.__setattr__(self, "transactions", transactions)
        object.__setattr__(self, "violations", violations)
        object.__setattr__(
            self,
            "transaction_plan_identity",
            _identity(
                "rfc011-transaction-plan-sha256",
                {
                    "decision_slot": self.decision_slot,
                    "instruction_identities": [
                        value.instruction_identity for value in instructions
                    ],
                    "planned_priority_fees_lamports": (
                        self.planned_priority_fees_lamports
                    ),
                    "planned_transaction_fees_lamports": (
                        self.planned_transaction_fees_lamports
                    ),
                    "protocol_deployment_plan_identity": (
                        self.protocol_deployment_plan_identity
                    ),
                    "round_identifier": self.round_identifier,
                    "scenario_identity": self.scenario_identity,
                    "transaction_identities": [
                        value.transaction_identity for value in transactions
                    ],
                    "transaction_model_identity": self.transaction_model_identity,
                    "violations": [_violation_payload(value) for value in violations],
                },
            ),
        )

    @property
    def transaction_count(self) -> int:
        return len(self.transactions)

    @property
    def is_feasible(self) -> bool:
        return not self.violations


@dataclass(frozen=True, slots=True)
class TransactionInclusionResult:
    """Immutable modeled inclusion result for one transaction plan."""

    transaction_plan_identity: str
    protocol_deployment_plan_identity: str
    scenario_identity: str
    inclusion_model_identity: str
    status: TransactionInclusionStatus
    assumed_submission_slots: tuple[int, ...]
    assumed_inclusion_slots: tuple[int, ...]
    modeled_transaction_costs_lamports: int
    modeled_priority_costs_lamports: int
    rejection_reasons: tuple[TransactionViolation, ...]
    result_identity: str = field(init=False)

    def __post_init__(self) -> None:
        _validate_canonical_string(
            "transaction_plan_identity",
            self.transaction_plan_identity,
        )
        _validate_canonical_string(
            "protocol_deployment_plan_identity",
            self.protocol_deployment_plan_identity,
        )
        _validate_canonical_string(
            "scenario_identity",
            self.scenario_identity,
        )
        _validate_canonical_string(
            "inclusion_model_identity",
            self.inclusion_model_identity,
        )
        if not isinstance(self.status, TransactionInclusionStatus):
            raise TypeError("status must be a TransactionInclusionStatus")
        submissions = tuple(self.assumed_submission_slots)
        inclusions = tuple(self.assumed_inclusion_slots)
        if len(submissions) != len(inclusions):
            raise ValueError("submission and inclusion slots must align")
        for name, values in (
            ("assumed_submission_slots", submissions),
            ("assumed_inclusion_slots", inclusions),
        ):
            if any(
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
                for value in values
            ):
                raise ValueError(f"{name} must contain nonnegative integers")
        if any(inclusion < submission for submission, inclusion in zip(
            submissions,
            inclusions,
            strict=True,
        )):
            raise ValueError("inclusion slots cannot precede submission slots")
        _validate_nonnegative_integer(
            "modeled_transaction_costs_lamports",
            self.modeled_transaction_costs_lamports,
        )
        _validate_nonnegative_integer(
            "modeled_priority_costs_lamports",
            self.modeled_priority_costs_lamports,
        )
        reasons = tuple(self.rejection_reasons)
        if not all(isinstance(value, TransactionViolation) for value in reasons):
            raise TypeError("rejection reasons must be TransactionViolation values")
        if len({value.code for value in reasons}) != len(reasons):
            raise ValueError("rejection reason codes must be unique")
        if self.status is TransactionInclusionStatus.INCLUDED and reasons:
            raise ValueError("included results cannot contain rejection reasons")
        if self.status is TransactionInclusionStatus.UNINCLUDED and not reasons:
            raise ValueError("unincluded results require rejection reasons")
        object.__setattr__(self, "assumed_submission_slots", submissions)
        object.__setattr__(self, "assumed_inclusion_slots", inclusions)
        object.__setattr__(self, "rejection_reasons", reasons)
        object.__setattr__(
            self,
            "result_identity",
            _identity(
                "rfc011-transaction-inclusion-result-sha256",
                {
                    "assumed_inclusion_slots": list(inclusions),
                    "assumed_submission_slots": list(submissions),
                    "inclusion_model_identity": self.inclusion_model_identity,
                    "modeled_priority_costs_lamports": (
                        self.modeled_priority_costs_lamports
                    ),
                    "modeled_transaction_costs_lamports": (
                        self.modeled_transaction_costs_lamports
                    ),
                    "rejection_reasons": [
                        _violation_payload(value) for value in reasons
                    ],
                    "status": self.status.value,
                    "protocol_deployment_plan_identity": (
                        self.protocol_deployment_plan_identity
                    ),
                    "scenario_identity": self.scenario_identity,
                    "transaction_plan_identity": self.transaction_plan_identity,
                },
            ),
        )

    @property
    def included(self) -> bool:
        return self.status is TransactionInclusionStatus.INCLUDED


@dataclass(frozen=True, slots=True)
class InclusionModel:
    """Apply deterministic offline inclusion assumptions to a plan."""

    model_identity: str

    def __post_init__(self) -> None:
        _validate_canonical_string("model_identity", self.model_identity)

    def evaluate(
        self,
        plan: TransactionPlan,
        scenario: EconomicScenario,
        *,
        round_deadline_slot: int,
    ) -> TransactionInclusionResult:
        """Return included or fail-closed unincluded status."""

        if not isinstance(plan, TransactionPlan):
            raise TypeError("plan must be a TransactionPlan")
        if not isinstance(scenario, EconomicScenario):
            raise TypeError("scenario must be an EconomicScenario")
        _validate_nonnegative_integer("round_deadline_slot", round_deadline_slot)

        reasons = list(plan.violations)
        if (
            plan.scenario_identity != scenario.scenario_identity
            and not any(
                value.code
                is TransactionViolationCode.SCENARIO_IDENTITY_MISMATCH
                for value in reasons
            )
        ):
            reasons.append(
                _violation(
                    TransactionViolationCode.SCENARIO_IDENTITY_MISMATCH,
                    "transaction plan scenario identity does not match the scenario",
                )
            )
        if self.model_identity != scenario.component_identities.inclusion_model:
            reasons.append(
                _violation(
                    TransactionViolationCode.INCLUSION_MODEL_IDENTITY_MISMATCH,
                    "inclusion model identity does not match the scenario",
                )
            )
        late_transactions = tuple(
            transaction.sequence_number
            for transaction in plan.transactions
            if transaction.assumed_inclusion_slot >= round_deadline_slot
        )
        if late_transactions:
            reasons.append(
                _violation(
                    TransactionViolationCode.ROUND_DEADLINE_REACHED,
                    "modeled inclusion must occur before the round deadline",
                    transactions=late_transactions,
                )
            )

        included = not reasons
        submissions = tuple(
            value.assumed_submission_slot for value in plan.transactions
        )
        inclusions = tuple(
            value.assumed_inclusion_slot for value in plan.transactions
        )
        if included:
            transaction_costs = plan.planned_transaction_fees_lamports
            priority_costs = plan.planned_priority_fees_lamports
        elif plan.transactions and not plan.violations:
            transaction_costs = (
                scenario.fee_assumptions.failed_transaction_fee_lamports
                * plan.transaction_count
            )
            priority_costs = 0
        else:
            transaction_costs = 0
            priority_costs = 0
        return TransactionInclusionResult(
            transaction_plan_identity=plan.transaction_plan_identity,
            protocol_deployment_plan_identity=(
                plan.protocol_deployment_plan_identity
            ),
            scenario_identity=plan.scenario_identity,
            inclusion_model_identity=self.model_identity,
            status=(
                TransactionInclusionStatus.INCLUDED
                if included
                else TransactionInclusionStatus.UNINCLUDED
            ),
            assumed_submission_slots=submissions,
            assumed_inclusion_slots=inclusions,
            modeled_transaction_costs_lamports=transaction_costs,
            modeled_priority_costs_lamports=priority_costs,
            rejection_reasons=tuple(reasons),
        )


@dataclass(frozen=True, slots=True)
class TransactionModel:
    """Build deterministic ORE instruction and transaction plans offline."""

    model_identity: str

    def __post_init__(self) -> None:
        _validate_canonical_string("model_identity", self.model_identity)

    def plan(
        self,
        deployment: ProtocolDeploymentPlan,
        scenario: EconomicScenario,
        *,
        decision_slot: int,
    ) -> TransactionPlan:
        """Pack a pre-transaction plan without constructing transactions."""

        if not isinstance(deployment, ProtocolDeploymentPlan):
            raise TypeError("deployment must be a ProtocolDeploymentPlan")
        if not isinstance(scenario, EconomicScenario):
            raise TypeError("scenario must be an EconomicScenario")
        _validate_nonnegative_integer("decision_slot", decision_slot)
        assumptions = scenario.transaction_assumptions
        violations: list[TransactionViolation] = []
        if deployment.protocol_revision != scenario.protocol_revision:
            violations.append(
                _violation(
                    TransactionViolationCode.PROTOCOL_REVISION_MISMATCH,
                    "deployment protocol revision does not match the scenario",
                )
            )
        if deployment.scenario_identity != scenario.scenario_identity:
            violations.append(
                _violation(
                    TransactionViolationCode.SCENARIO_IDENTITY_MISMATCH,
                    "deployment scenario identity does not match the scenario",
                )
            )
        if self.model_identity != scenario.component_identities.transaction_model:
            violations.append(
                _violation(
                    TransactionViolationCode.TRANSACTION_MODEL_IDENTITY_MISMATCH,
                    "transaction model identity does not match the scenario",
                )
            )

        instructions = _pack_deploy_instructions(deployment, scenario)
        if (
            assumptions.transaction_base_size_bytes
            > assumptions.maximum_transaction_size_bytes
        ):
            violations.append(
                _violation(
                    TransactionViolationCode.TRANSACTION_BASE_SIZE_EXCEEDED,
                    "transaction base size exceeds the configured maximum",
                )
            )
        if (
            assumptions.transaction_base_compute_units
            > assumptions.compute_unit_limit
        ):
            violations.append(
                _violation(
                    TransactionViolationCode.TRANSACTION_BASE_COMPUTE_EXCEEDED,
                    "transaction base compute exceeds the configured limit",
                )
            )
        oversized = tuple(
            value.instruction_identity
            for value in instructions
            if assumptions.transaction_base_size_bytes
            + value.assumed_size_bytes
            > assumptions.maximum_transaction_size_bytes
        )
        if oversized:
            violations.append(
                _violation(
                    TransactionViolationCode.INSTRUCTION_SIZE_EXCEEDED,
                    "a Deploy instruction cannot fit in one transaction",
                    instructions=oversized,
                )
            )
        overcompute = tuple(
            value.instruction_identity
            for value in instructions
            if assumptions.transaction_base_compute_units
            + value.assumed_compute_units
            > assumptions.compute_unit_limit
        )
        if overcompute:
            violations.append(
                _violation(
                    TransactionViolationCode.INSTRUCTION_COMPUTE_EXCEEDED,
                    "a Deploy instruction exceeds one transaction compute limit",
                    instructions=overcompute,
                )
            )

        intrinsic_codes = {
            TransactionViolationCode.TRANSACTION_BASE_SIZE_EXCEEDED,
            TransactionViolationCode.TRANSACTION_BASE_COMPUTE_EXCEEDED,
            TransactionViolationCode.INSTRUCTION_SIZE_EXCEEDED,
            TransactionViolationCode.INSTRUCTION_COMPUTE_EXCEEDED,
        }
        if any(value.code in intrinsic_codes for value in violations):
            transactions: tuple[PlannedTransaction, ...] = ()
        else:
            transactions = _group_transactions(
                instructions,
                scenario,
                decision_slot,
            )

        base_fees = (
            len(transactions)
            * scenario.fee_assumptions.base_transaction_fee_lamports
        )
        priority_fees = (
            len(transactions)
            * scenario.fee_assumptions.priority_fee_lamports
        )
        if (
            base_fees + priority_fees
            > scenario.capital_reserve_rules.transaction_cost_reserve_lamports
        ):
            violations.append(
                _violation(
                    TransactionViolationCode.TRANSACTION_COST_RESERVE_EXCEEDED,
                    "planned transaction costs exceed the configured reserve",
                )
            )
        return TransactionPlan(
            protocol_deployment_plan_identity=(
                protocol_deployment_plan_identity(deployment)
            ),
            scenario_identity=scenario.scenario_identity,
            transaction_model_identity=self.model_identity,
            round_identifier=deployment.round_identifier,
            decision_slot=decision_slot,
            instructions=instructions,
            transactions=transactions,
            planned_transaction_fees_lamports=base_fees,
            planned_priority_fees_lamports=priority_fees,
            violations=tuple(violations),
        )

    def evaluate(
        self,
        deployment: ProtocolDeploymentPlan,
        scenario: EconomicScenario,
        *,
        decision_slot: int,
        round_deadline_slot: int,
    ) -> TransactionInclusionResult:
        """Plan and evaluate inclusion under scenario-bound assumptions."""

        plan = self.plan(deployment, scenario, decision_slot=decision_slot)
        inclusion = InclusionModel(
            scenario.component_identities.inclusion_model
        )
        return inclusion.evaluate(
            plan,
            scenario,
            round_deadline_slot=round_deadline_slot,
        )


def _pack_deploy_instructions(
    deployment: ProtocolDeploymentPlan,
    scenario: EconomicScenario,
) -> tuple[DeployInstruction, ...]:
    grouped: dict[int, list[int]] = {}
    for square, amount in enumerate(deployment.deployed_lamports):
        if amount > 0:
            grouped.setdefault(amount, []).append(square)
    assumptions = scenario.transaction_assumptions
    return tuple(
        DeployInstruction(
            amount_lamports=amount,
            square_identifiers=tuple(squares),
            square_mask=sum(1 << square for square in squares),
            assumed_size_bytes=assumptions.deploy_instruction_size_bytes,
            assumed_compute_units=(
                assumptions.deploy_instruction_compute_units
            ),
        )
        for amount, squares in grouped.items()
    )


def _group_transactions(
    instructions: tuple[DeployInstruction, ...],
    scenario: EconomicScenario,
    decision_slot: int,
) -> tuple[PlannedTransaction, ...]:
    if not instructions:
        return ()
    assumptions = scenario.transaction_assumptions
    groups: list[list[DeployInstruction]] = []
    current: list[DeployInstruction] = []
    current_size = assumptions.transaction_base_size_bytes
    current_compute = assumptions.transaction_base_compute_units
    for instruction in instructions:
        exceeds = current and (
            len(current) >= assumptions.maximum_instructions_per_transaction
            or current_size + instruction.assumed_size_bytes
            > assumptions.maximum_transaction_size_bytes
            or current_compute + instruction.assumed_compute_units
            > assumptions.compute_unit_limit
        )
        if exceeds:
            groups.append(current)
            current = []
            current_size = assumptions.transaction_base_size_bytes
            current_compute = assumptions.transaction_base_compute_units
        current.append(instruction)
        current_size += instruction.assumed_size_bytes
        current_compute += instruction.assumed_compute_units
    groups.append(current)

    first_submission_slot = decision_slot + assumptions.submission_delay_slots
    return tuple(
        PlannedTransaction(
            sequence_number=index + 1,
            instructions=tuple(group),
            assumed_size_bytes=(
                assumptions.transaction_base_size_bytes
                + sum(value.assumed_size_bytes for value in group)
            ),
            assumed_compute_units=(
                assumptions.transaction_base_compute_units
                + sum(value.assumed_compute_units for value in group)
            ),
            assumed_submission_slot=(
                first_submission_slot
                + index // assumptions.maximum_transactions_per_slot
            ),
            assumed_inclusion_slot=(
                first_submission_slot
                + index // assumptions.maximum_transactions_per_slot
                + assumptions.inclusion_latency_slots
            ),
        )
        for index, group in enumerate(groups)
    )


def protocol_deployment_plan_identity(
    deployment: ProtocolDeploymentPlan,
) -> str:
    return _identity(
        "rfc011-protocol-deployment-plan-sha256",
        {
            "deployed_lamports": list(deployment.deployed_lamports),
            "occupied_square_count": deployment.occupied_square_count,
            "participant_state_identity": deployment.participant_state_identity,
            "protocol_revision": deployment.protocol_revision,
            "round_identifier": deployment.round_identifier,
            "scenario_identity": deployment.scenario_identity,
            "total_deployed_lamports": deployment.total_deployed_lamports,
        },
    )


def _violation(
    code: TransactionViolationCode,
    message: str,
    *,
    instructions: tuple[str, ...] = (),
    transactions: tuple[int, ...] = (),
) -> TransactionViolation:
    return TransactionViolation(
        code=code,
        message=message,
        instruction_identifiers=instructions,
        transaction_sequence_numbers=transactions,
    )


def _violation_payload(value: TransactionViolation) -> dict[str, Any]:
    return {
        "code": value.code.value,
        "instruction_identifiers": list(value.instruction_identifiers),
        "message": value.message,
        "transaction_sequence_numbers": list(
            value.transaction_sequence_numbers
        ),
    }


def _identity(prefix: str, payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(encoded).hexdigest()}"


def _validate_canonical_string(name: str, value: object) -> None:
    if (
        not isinstance(value, str)
        or not value
        or value.strip() != value
    ):
        raise ValueError(f"{name} must be a nonempty canonical string")


def _validate_nonnegative_integer(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")


def _validate_positive_integer(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")


__all__ = (
    "DeployInstruction",
    "InclusionModel",
    "PlannedTransaction",
    "TransactionInclusionResult",
    "TransactionInclusionStatus",
    "TransactionModel",
    "TransactionPlan",
    "TransactionViolation",
    "TransactionViolationCode",
    "protocol_deployment_plan_identity",
)
