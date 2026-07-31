"""RFC-011 Phase 3 pre-transaction protocol constraint validation."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from orev3.strategy_lab.economics import (
    SQUARE_COUNT,
    CheckpointState,
    EconomicScenario,
    ParticipantEconomicState,
)


class ProtocolConstraintCode(str, Enum):
    """Stable identifiers for pre-transaction constraint failures."""

    DEPLOYMENT_VECTOR_TYPE = "deployment_vector_type"
    DEPLOYMENT_VECTOR_LENGTH = "deployment_vector_length"
    INVALID_SQUARE_IDENTIFIER = "invalid_square_identifier"
    DEPLOYMENT_LAMPORT_TYPE = "deployment_lamport_type"
    DEPLOYMENT_LAMPORT_NEGATIVE = "deployment_lamport_negative"
    OCCUPIED_SQUARE = "occupied_square"
    AUTHORITY_STATE_INCONSISTENT = "authority_state_inconsistent"
    CURRENT_ROUND_INCONSISTENT = "current_round_inconsistent"
    CHECKPOINT_REQUIRED = "checkpoint_required"
    PROTOCOL_REVISION_MISMATCH = "protocol_revision_mismatch"
    AVAILABLE_BALANCE_EXCEEDED = "available_balance_exceeded"
    CAPITAL_RESERVE_INSUFFICIENT = "capital_reserve_insufficient"
    DEPLOYMENT_BUDGET_EXCEEDED = "deployment_budget_exceeded"


@dataclass(frozen=True, slots=True)
class ProtocolConstraintViolation:
    """One immutable failed pre-transaction constraint."""

    code: ProtocolConstraintCode
    message: str
    square_identifiers: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.code, ProtocolConstraintCode):
            raise TypeError("code must be a ProtocolConstraintCode")
        if (
            not isinstance(self.message, str)
            or not self.message
            or self.message.strip() != self.message
        ):
            raise ValueError("message must be a nonempty canonical string")
        squares = tuple(self.square_identifiers)
        if any(
            isinstance(square, bool) or not isinstance(square, int)
            for square in squares
        ):
            raise TypeError("square identifiers must be integers")
        if tuple(sorted(set(squares))) != squares:
            raise ValueError(
                "square identifiers must be unique and ascending"
            )
        object.__setattr__(self, "square_identifiers", squares)


@dataclass(frozen=True, slots=True)
class ProtocolDeploymentPlan:
    """One immutable pre-transaction-feasible deployment."""

    deployed_lamports: tuple[int, ...]
    total_deployed_lamports: int
    occupied_square_count: int
    protocol_revision: str
    scenario_identity: str
    participant_state_identity: str
    round_identifier: int

    def __post_init__(self) -> None:
        deployed = tuple(self.deployed_lamports)
        if len(deployed) != SQUARE_COUNT:
            raise ValueError("deployed_lamports must contain 25 values")
        if any(
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
            for value in deployed
        ):
            raise ValueError(
                "deployed_lamports must contain nonnegative integers"
            )
        if self.total_deployed_lamports != sum(deployed):
            raise ValueError("total deployed lamports is inconsistent")
        if self.occupied_square_count != sum(value > 0 for value in deployed):
            raise ValueError("occupied square count is inconsistent")
        if (
            isinstance(self.round_identifier, bool)
            or not isinstance(self.round_identifier, int)
            or self.round_identifier < 0
        ):
            raise ValueError("round_identifier must be nonnegative")
        for name, value in (
            ("protocol_revision", self.protocol_revision),
            ("scenario_identity", self.scenario_identity),
            ("participant_state_identity", self.participant_state_identity),
        ):
            if (
                not isinstance(value, str)
                or not value
                or value.strip() != value
            ):
                raise ValueError(f"{name} must be a canonical string")
        object.__setattr__(self, "deployed_lamports", deployed)

    @property
    def square_identifiers(self) -> tuple[int, ...]:
        """Return the unique positional square domain for this plan."""

        return tuple(range(SQUARE_COUNT))


@dataclass(frozen=True, slots=True)
class ProtocolRejection:
    """Immutable aggregate of every detected protocol constraint failure."""

    violations: tuple[ProtocolConstraintViolation, ...]
    scenario_identity: str
    participant_state_identity: str

    def __post_init__(self) -> None:
        violations = tuple(self.violations)
        if not violations:
            raise ValueError("a protocol rejection requires violations")
        if not all(
            isinstance(value, ProtocolConstraintViolation)
            for value in violations
        ):
            raise TypeError(
                "violations must contain ProtocolConstraintViolation values"
            )
        codes = tuple(value.code for value in violations)
        if len(set(codes)) != len(codes):
            raise ValueError("protocol violation codes must be unique")
        for name, value in (
            ("scenario_identity", self.scenario_identity),
            ("participant_state_identity", self.participant_state_identity),
        ):
            if not isinstance(value, str) or not value:
                raise ValueError(f"{name} must be nonempty")
        object.__setattr__(self, "violations", violations)


@dataclass(frozen=True, slots=True)
class ProtocolConstraintModel:
    """Validate constraints knowable before transaction planning."""

    protocol_revision: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.protocol_revision, str)
            or not self.protocol_revision
            or self.protocol_revision.strip() != self.protocol_revision
        ):
            raise ValueError(
                "protocol_revision must be a nonempty canonical string"
            )

    def validate(
        self,
        proposed_deployment: tuple[int, ...],
        scenario: EconomicScenario,
        participant_state: ParticipantEconomicState,
    ) -> ProtocolDeploymentPlan | ProtocolRejection:
        """Return a feasible plan or all detected constraint violations."""

        if not isinstance(scenario, EconomicScenario):
            raise TypeError("scenario must be an EconomicScenario")
        if not isinstance(participant_state, ParticipantEconomicState):
            raise TypeError(
                "participant_state must be a ParticipantEconomicState"
            )

        violations: list[ProtocolConstraintViolation] = []
        vector_is_tuple = isinstance(proposed_deployment, tuple)
        if not vector_is_tuple:
            violations.append(
                _violation(
                    ProtocolConstraintCode.DEPLOYMENT_VECTOR_TYPE,
                    "proposed deployment must be one immutable tuple",
                )
            )
            proposed = tuple(proposed_deployment) if isinstance(
                proposed_deployment,
                (list, tuple),
            ) else ()
        else:
            proposed = proposed_deployment

        if len(proposed) != SQUARE_COUNT:
            violations.append(
                _violation(
                    ProtocolConstraintCode.DEPLOYMENT_VECTOR_LENGTH,
                    "proposed deployment must contain exactly 25 positions",
                )
            )
        invalid_squares = tuple(range(SQUARE_COUNT, len(proposed)))
        if invalid_squares:
            violations.append(
                _violation(
                    ProtocolConstraintCode.INVALID_SQUARE_IDENTIFIER,
                    "proposed deployment contains positions outside 0..24",
                    invalid_squares,
                )
            )

        noninteger_squares = tuple(
            index
            for index, value in enumerate(proposed[:SQUARE_COUNT])
            if isinstance(value, bool) or not isinstance(value, int)
        )
        if noninteger_squares:
            violations.append(
                _violation(
                    ProtocolConstraintCode.DEPLOYMENT_LAMPORT_TYPE,
                    "deployed square amounts must be integer lamports",
                    noninteger_squares,
                )
            )
        negative_squares = tuple(
            index
            for index, value in enumerate(proposed[:SQUARE_COUNT])
            if isinstance(value, int)
            and not isinstance(value, bool)
            and value < 0
        )
        if negative_squares:
            violations.append(
                _violation(
                    ProtocolConstraintCode.DEPLOYMENT_LAMPORT_NEGATIVE,
                    "deployed square amounts must be positive or zero",
                    negative_squares,
                )
            )

        numeric_vector = (
            len(proposed) == SQUARE_COUNT
            and not noninteger_squares
            and not negative_squares
        )
        total_deployed = sum(proposed) if numeric_vector else None
        if numeric_vector:
            occupied_squares = tuple(
                index
                for index, (prior, requested) in enumerate(
                    zip(
                        participant_state.occupied_squares,
                        proposed,
                        strict=True,
                    )
                )
                if prior and requested > 0
            )
            if occupied_squares:
                violations.append(
                    _violation(
                        ProtocolConstraintCode.OCCUPIED_SQUARE,
                        "an authority-round-square may receive one deployment",
                        occupied_squares,
                    )
                )

        try:
            state_identity_is_consistent = (
                replace(participant_state).state_identity
                == participant_state.state_identity
            )
        except (TypeError, ValueError):
            state_identity_is_consistent = False
        if not state_identity_is_consistent:
            violations.append(
                _violation(
                    ProtocolConstraintCode.AUTHORITY_STATE_INCONSISTENT,
                    "participant authority state identity is inconsistent",
                )
            )

        current_round = participant_state.current_round
        if (
            isinstance(current_round, bool)
            or not isinstance(current_round, int)
            or current_round < 0
            or (
                participant_state.last_economically_settled_round is not None
                and participant_state.last_economically_settled_round
                > current_round
            )
        ):
            violations.append(
                _violation(
                    ProtocolConstraintCode.CURRENT_ROUND_INCONSISTENT,
                    "participant state does not identify a consistent round",
                )
            )

        if participant_state.checkpoint_state is CheckpointState.REQUIRED:
            violations.append(
                _violation(
                    ProtocolConstraintCode.CHECKPOINT_REQUIRED,
                    "the prior round requires checkpoint completion",
                )
            )

        if scenario.protocol_revision != self.protocol_revision:
            violations.append(
                _violation(
                    ProtocolConstraintCode.PROTOCOL_REVISION_MISMATCH,
                    "scenario protocol revision is incompatible with model",
                )
            )

        if total_deployed is not None:
            available = participant_state.available_sol_lamports
            reserves = scenario.capital_reserve_rules.total_reserved_lamports
            if total_deployed > available:
                violations.append(
                    _violation(
                        ProtocolConstraintCode.AVAILABLE_BALANCE_EXCEEDED,
                        "proposed deployment exceeds available SOL",
                    )
                )
            if available - total_deployed < reserves:
                violations.append(
                    _violation(
                        ProtocolConstraintCode.CAPITAL_RESERVE_INSUFFICIENT,
                        "proposed deployment would consume required reserves",
                    )
                )
            if total_deployed > (
                scenario.per_round_deployment_budget_lamports
            ):
                violations.append(
                    _violation(
                        ProtocolConstraintCode.DEPLOYMENT_BUDGET_EXCEEDED,
                        "proposed deployment exceeds the per-round budget",
                    )
                )

        if violations:
            return ProtocolRejection(
                violations=tuple(violations),
                scenario_identity=scenario.scenario_identity,
                participant_state_identity=participant_state.state_identity,
            )

        assert total_deployed is not None
        assert isinstance(current_round, int) and not isinstance(
            current_round,
            bool,
        )
        return ProtocolDeploymentPlan(
            deployed_lamports=proposed,
            total_deployed_lamports=total_deployed,
            occupied_square_count=sum(value > 0 for value in proposed),
            protocol_revision=self.protocol_revision,
            scenario_identity=scenario.scenario_identity,
            participant_state_identity=participant_state.state_identity,
            round_identifier=current_round,
        )


def _violation(
    code: ProtocolConstraintCode,
    message: str,
    squares: tuple[int, ...] = (),
) -> ProtocolConstraintViolation:
    return ProtocolConstraintViolation(
        code=code,
        message=message,
        square_identifiers=squares,
    )


__all__ = (
    "ProtocolConstraintCode",
    "ProtocolConstraintModel",
    "ProtocolConstraintViolation",
    "ProtocolDeploymentPlan",
    "ProtocolRejection",
)
