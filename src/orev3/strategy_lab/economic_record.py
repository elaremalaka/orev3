"""Immutable RFC-011 Phase 8 economic simulation records."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from fractions import Fraction
from typing import Any

from orev3.strategy_lab.economic_metrics import EconomicExperimentMetrics
from orev3.strategy_lab.economics import (
    EconomicScenario,
    ParticipantEconomicState,
)
from orev3.strategy_lab.settlement import (
    EconomicRoundResult,
    EconomicRoundStatus,
)


@dataclass(frozen=True, slots=True)
class EconomicSimulationRecord:
    """Immutable evidence for one completed RFC-011 simulation interval."""

    rfc010_experiment_identity: str
    economic_scenario: EconomicScenario
    initial_participant_state: ParticipantEconomicState
    terminal_participant_state: ParticipantEconomicState
    ordered_economic_round_results: tuple[EconomicRoundResult, ...]
    economic_experiment_metrics: EconomicExperimentMetrics
    replay_identity: str
    economic_scenario_identity: str = field(init=False)
    economic_scenario_sha256: str = field(init=False)
    protocol_revision: str = field(init=False)
    dataset_identity: str = field(init=False)
    allocation_materializer_identity: str = field(init=False)
    protocol_constraint_model_identity: str = field(init=False)
    transaction_model_identity: str = field(init=False)
    inclusion_model_identity: str = field(init=False)
    ore_settlement_model_identity: str = field(init=False)
    economic_simulation_runner_identity: str = field(init=False)
    economic_metrics_engine_identity: str = field(init=False)
    initial_participant_state_sha256: str = field(init=False)
    terminal_participant_state_sha256: str = field(init=False)
    ordered_economic_round_result_identities: tuple[str, ...] = field(
        init=False,
    )
    deterministic_result_sha256: str = field(init=False)
    record_identity: str = field(init=False)

    def __post_init__(self) -> None:
        _validate_identity(
            "rfc010_experiment_identity",
            self.rfc010_experiment_identity,
        )
        _validate_identity("replay_identity", self.replay_identity)
        if not isinstance(self.economic_scenario, EconomicScenario):
            raise TypeError("economic_scenario must be an EconomicScenario")
        if not isinstance(
            self.initial_participant_state,
            ParticipantEconomicState,
        ):
            raise TypeError(
                "initial_participant_state must be ParticipantEconomicState"
            )
        if not isinstance(
            self.terminal_participant_state,
            ParticipantEconomicState,
        ):
            raise TypeError(
                "terminal_participant_state must be ParticipantEconomicState"
            )
        if not isinstance(
            self.economic_experiment_metrics,
            EconomicExperimentMetrics,
        ):
            raise TypeError(
                "economic_experiment_metrics must be EconomicExperimentMetrics"
            )
        results = self.ordered_economic_round_results
        if not isinstance(results, tuple) or not all(
            isinstance(value, EconomicRoundResult) for value in results
        ):
            raise TypeError(
                "ordered_economic_round_results must be an immutable "
                "EconomicRoundResult tuple"
            )

        scenario = self.economic_scenario
        initial_state = self.initial_participant_state
        terminal_state = self.terminal_participant_state
        metrics = self.economic_experiment_metrics
        _validate_immutable_identity(
            "economic scenario",
            scenario,
            "scenario_identity",
        )
        _validate_immutable_identity(
            "initial participant state",
            initial_state,
            "state_identity",
        )
        _validate_immutable_identity(
            "terminal participant state",
            terminal_state,
            "state_identity",
        )
        _validate_immutable_identity(
            "economic metrics",
            metrics,
            "metrics_identity",
        )
        if self.replay_identity != scenario.replay_identity:
            raise ValueError("replay identity does not match the scenario")
        if results:
            if metrics.scenario_identity != scenario.scenario_identity:
                raise ValueError("economic metrics do not match the scenario")
            if metrics.protocol_revision != scenario.protocol_revision:
                raise ValueError(
                    "economic metrics protocol revision is inconsistent"
                )
        elif (
            metrics.scenario_identity is not None
            or metrics.protocol_revision is not None
        ):
            raise ValueError("empty economic metrics cannot claim run bindings")
        if (
            metrics.metrics_engine_identity
            != scenario.component_identities.metrics_engine
        ):
            raise ValueError("economic metrics engine identity is inconsistent")

        identities = _validate_ordered_results(results, scenario)
        _validate_metric_evidence(metrics, results)
        if results:
            if (
                results[0].participant_state_before_identity
                != initial_state.state_identity
            ):
                raise ValueError(
                    "first economic result is not bound to the initial state"
                )
            if (
                results[-1].participant_state_after.state_identity
                != terminal_state.state_identity
            ):
                raise ValueError(
                    "last economic result is not bound to the terminal state"
                )
        elif terminal_state.state_identity != initial_state.state_identity:
            raise ValueError(
                "an empty simulation must preserve its initial state"
            )

        components = scenario.component_identities
        object.__setattr__(
            self,
            "ordered_economic_round_results",
            results,
        )
        object.__setattr__(
            self,
            "economic_scenario_identity",
            scenario.scenario_identity,
        )
        object.__setattr__(
            self,
            "economic_scenario_sha256",
            _sha256_from_identity(
                "economic_scenario.scenario_identity",
                scenario.scenario_identity,
                "rfc011-economic-scenario-sha256",
            ),
        )
        object.__setattr__(self, "protocol_revision", scenario.protocol_revision)
        object.__setattr__(self, "dataset_identity", scenario.dataset_identity)
        object.__setattr__(
            self,
            "allocation_materializer_identity",
            components.allocation_materializer,
        )
        object.__setattr__(
            self,
            "protocol_constraint_model_identity",
            components.protocol_constraint_model,
        )
        object.__setattr__(
            self,
            "transaction_model_identity",
            components.transaction_model,
        )
        object.__setattr__(
            self,
            "inclusion_model_identity",
            components.inclusion_model,
        )
        object.__setattr__(
            self,
            "ore_settlement_model_identity",
            components.settlement_model,
        )
        object.__setattr__(
            self,
            "economic_simulation_runner_identity",
            components.simulation_runner,
        )
        object.__setattr__(
            self,
            "economic_metrics_engine_identity",
            components.metrics_engine,
        )
        object.__setattr__(
            self,
            "initial_participant_state_sha256",
            _sha256_from_identity(
                "initial_participant_state.state_identity",
                initial_state.state_identity,
                "rfc011-participant-state-sha256",
            ),
        )
        object.__setattr__(
            self,
            "terminal_participant_state_sha256",
            _sha256_from_identity(
                "terminal_participant_state.state_identity",
                terminal_state.state_identity,
                "rfc011-participant-state-sha256",
            ),
        )
        object.__setattr__(
            self,
            "ordered_economic_round_result_identities",
            identities,
        )
        object.__setattr__(
            self,
            "deterministic_result_sha256",
            _sha256(
                {
                    "economic_experiment_metrics_identity": (
                        metrics.metrics_identity
                    ),
                    "ordered_economic_round_result_identities": list(
                        identities
                    ),
                }
            ),
        )
        object.__setattr__(
            self,
            "record_identity",
            _identity(
                "rfc011-economic-simulation-record-sha256",
                self._identity_payload(),
            ),
        )

    @property
    def completeness_metadata(
        self,
    ) -> tuple[tuple[str, int | Fraction | None], ...]:
        """Return canonical completeness evidence without recomputation."""

        metrics = self.economic_experiment_metrics
        return (
            (
                "economically_processed_round_count",
                metrics.economically_processed_round_count,
            ),
            (
                "outcome_complete_round_count",
                metrics.observed_outcome_count + metrics.enriched_outcome_count,
            ),
            ("missing_outcome_round_count", metrics.missing_outcome_count),
            ("completeness_percentage", metrics.completeness_percentage),
        )

    @property
    def outcome_provenance_summary(self) -> tuple[tuple[str, int], ...]:
        """Return the Phase 7 provenance summary exactly as recorded."""

        return self.economic_experiment_metrics.provenance_summary

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "allocation_materializer_identity": (
                self.allocation_materializer_identity
            ),
            "completeness_metadata": _plain_value(
                self.completeness_metadata
            ),
            "dataset_identity": self.dataset_identity,
            "deterministic_result_sha256": self.deterministic_result_sha256,
            "economic_experiment_metrics_identity": (
                self.economic_experiment_metrics.metrics_identity
            ),
            "economic_metrics_engine_identity": (
                self.economic_metrics_engine_identity
            ),
            "economic_scenario_identity": self.economic_scenario_identity,
            "economic_scenario_sha256": self.economic_scenario_sha256,
            "economic_simulation_runner_identity": (
                self.economic_simulation_runner_identity
            ),
            "inclusion_model_identity": self.inclusion_model_identity,
            "initial_participant_state_sha256": (
                self.initial_participant_state_sha256
            ),
            "ore_settlement_model_identity": (
                self.ore_settlement_model_identity
            ),
            "ordered_economic_round_result_identities": list(
                self.ordered_economic_round_result_identities
            ),
            "outcome_provenance_summary": _plain_value(
                self.outcome_provenance_summary
            ),
            "protocol_constraint_model_identity": (
                self.protocol_constraint_model_identity
            ),
            "protocol_revision": self.protocol_revision,
            "replay_identity": self.replay_identity,
            "rfc010_experiment_identity": self.rfc010_experiment_identity,
            "terminal_participant_state_sha256": (
                self.terminal_participant_state_sha256
            ),
            "transaction_model_identity": self.transaction_model_identity,
        }


def _validate_ordered_results(
    results: tuple[EconomicRoundResult, ...],
    scenario: EconomicScenario,
) -> tuple[str, ...]:
    identities: list[str] = []
    round_identifiers: list[int] = []
    for result in results:
        _validate_immutable_identity(
            "economic round result",
            result,
            "result_identity",
        )
        _validate_immutable_identity(
            "economic round participant state",
            result.participant_state_after,
            "state_identity",
        )
        if result.round_identifier is None:
            raise ValueError("recorded economic results require round identity")
        if result.scenario_identity != scenario.scenario_identity:
            raise ValueError("economic result does not match the scenario")
        if result.protocol_revision != scenario.protocol_revision:
            raise ValueError("economic result protocol revision is inconsistent")
        identities.append(result.result_identity)
        round_identifiers.append(result.round_identifier)
    if len(set(identities)) != len(identities):
        raise ValueError("economic result identities must be unique")
    if len(set(round_identifiers)) != len(round_identifiers):
        raise ValueError("economic result round identities must be unique")
    return tuple(identities)


def _validate_metric_evidence(
    metrics: EconomicExperimentMetrics,
    results: tuple[EconomicRoundResult, ...],
) -> None:
    status_counts = {
        status: sum(result.status is status for result in results)
        for status in EconomicRoundStatus
    }
    if metrics.economically_processed_round_count != len(results):
        raise ValueError("metrics and economic result counts are inconsistent")
    for status, recorded in (
        (EconomicRoundStatus.SETTLED, metrics.settled_round_count),
        (EconomicRoundStatus.REJECTED, metrics.rejected_round_count),
        (EconomicRoundStatus.UNINCLUDED, metrics.unincluded_round_count),
        (
            EconomicRoundStatus.MISSING_OUTCOME,
            metrics.missing_outcome_round_count,
        ),
    ):
        if status_counts[status] != recorded:
            raise ValueError("metrics and economic result statuses are inconsistent")
    observed = sum(result.outcome_source == "observed" for result in results)
    enriched = sum(result.outcome_source == "enriched" for result in results)
    missing = sum(
        result.status is EconomicRoundStatus.MISSING_OUTCOME
        for result in results
    )
    if (
        observed != metrics.observed_outcome_count
        or enriched != metrics.enriched_outcome_count
        or missing != metrics.missing_outcome_count
    ):
        raise ValueError("metrics and outcome provenance are inconsistent")


def _validate_immutable_identity(
    name: str,
    value: object,
    attribute: str,
) -> None:
    try:
        rebuilt = replace(value)  # type: ignore[arg-type]
        identity_matches = getattr(rebuilt, attribute) == getattr(
            value,
            attribute,
        )
    except (AttributeError, TypeError, ValueError):
        identity_matches = False
    if not identity_matches:
        raise ValueError(f"{name} identity is inconsistent")


def _sha256_from_identity(name: str, value: str, prefix: str) -> str:
    expected = f"{prefix}:"
    if not value.startswith(expected):
        raise ValueError(f"{name} must use {prefix}")
    digest = value[len(expected):]
    if len(digest) != 64 or any(
        character not in "0123456789abcdef" for character in digest
    ):
        raise ValueError(f"{name} must contain a canonical SHA-256 digest")
    return digest


def _identity(prefix: str, payload: dict[str, Any]) -> str:
    return f"{prefix}:{_sha256(payload)}"


def _sha256(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _plain_value(value: Any) -> Any:
    if isinstance(value, Fraction):
        return {
            "denominator": value.denominator,
            "numerator": value.numerator,
        }
    if isinstance(value, tuple):
        return [_plain_value(item) for item in value]
    return value


def _validate_identity(name: str, value: object) -> None:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ValueError(f"{name} must be a nonempty canonical string")


__all__ = ("EconomicSimulationRecord",)
