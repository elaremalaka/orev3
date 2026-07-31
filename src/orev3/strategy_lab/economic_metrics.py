"""Deterministic RFC-011 Phase 7 economic experiment metrics."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from fractions import Fraction
from typing import Any

from orev3.strategy_lab.settlement import (
    EconomicRoundResult,
    EconomicRoundStatus,
    ORERewardTreatment,
)


@dataclass(frozen=True, slots=True)
class EconomicExperimentMetrics:
    """Immutable protocol-native aggregation of economic round results."""

    metrics_engine_identity: str
    scenario_identity: str | None
    protocol_revision: str | None
    economically_processed_round_count: int
    settled_round_count: int
    rejected_round_count: int
    unincluded_round_count: int
    missing_outcome_round_count: int
    total_deployed_lamports: int
    total_deployment_budget_lamports: int
    total_returned_principal_lamports: int
    total_sol_winnings_lamports: int
    total_returned_sol_lamports: int
    total_protocol_fees_lamports: int
    total_transaction_fees_lamports: int
    total_priority_fees_lamports: int
    total_checkpoint_costs_lamports: int
    total_gross_sol_outflow_lamports: int
    total_gross_sol_inflow_lamports: int
    net_sol_change_lamports: int
    maximum_concurrent_sol_exposure_lamports: int
    total_ore_earned_raw: int
    solo_reward_round_count: int
    split_reward_round_count: int
    winning_square_capital_share_sum: Fraction
    dilution_sum: Fraction
    capture_efficiency_ore_raw_numerator: int
    capture_efficiency_deployed_lamports_denominator: int
    observed_outcome_count: int
    enriched_outcome_count: int
    missing_outcome_count: int
    metrics_identity: str = field(init=False)

    def __post_init__(self) -> None:
        _validate_identity("metrics_engine_identity", self.metrics_engine_identity)
        for name, value in (
            ("scenario_identity", self.scenario_identity),
            ("protocol_revision", self.protocol_revision),
        ):
            if value is not None:
                _validate_identity(name, value)
        for name, value in (
            (
                "economically_processed_round_count",
                self.economically_processed_round_count,
            ),
            ("settled_round_count", self.settled_round_count),
            ("rejected_round_count", self.rejected_round_count),
            ("unincluded_round_count", self.unincluded_round_count),
            (
                "missing_outcome_round_count",
                self.missing_outcome_round_count,
            ),
            ("total_deployed_lamports", self.total_deployed_lamports),
            (
                "total_deployment_budget_lamports",
                self.total_deployment_budget_lamports,
            ),
            (
                "total_returned_principal_lamports",
                self.total_returned_principal_lamports,
            ),
            ("total_sol_winnings_lamports", self.total_sol_winnings_lamports),
            ("total_returned_sol_lamports", self.total_returned_sol_lamports),
            ("total_protocol_fees_lamports", self.total_protocol_fees_lamports),
            (
                "total_transaction_fees_lamports",
                self.total_transaction_fees_lamports,
            ),
            ("total_priority_fees_lamports", self.total_priority_fees_lamports),
            (
                "total_checkpoint_costs_lamports",
                self.total_checkpoint_costs_lamports,
            ),
            (
                "total_gross_sol_outflow_lamports",
                self.total_gross_sol_outflow_lamports,
            ),
            (
                "total_gross_sol_inflow_lamports",
                self.total_gross_sol_inflow_lamports,
            ),
            (
                "maximum_concurrent_sol_exposure_lamports",
                self.maximum_concurrent_sol_exposure_lamports,
            ),
            ("total_ore_earned_raw", self.total_ore_earned_raw),
            ("solo_reward_round_count", self.solo_reward_round_count),
            ("split_reward_round_count", self.split_reward_round_count),
            (
                "capture_efficiency_ore_raw_numerator",
                self.capture_efficiency_ore_raw_numerator,
            ),
            (
                "capture_efficiency_deployed_lamports_denominator",
                self.capture_efficiency_deployed_lamports_denominator,
            ),
            ("observed_outcome_count", self.observed_outcome_count),
            ("enriched_outcome_count", self.enriched_outcome_count),
            ("missing_outcome_count", self.missing_outcome_count),
        ):
            _validate_nonnegative_integer(name, value)
        if isinstance(self.net_sol_change_lamports, bool) or not isinstance(
            self.net_sol_change_lamports,
            int,
        ):
            raise TypeError("net_sol_change_lamports must be an integer")
        for name, value in (
            (
                "winning_square_capital_share_sum",
                self.winning_square_capital_share_sum,
            ),
            ("dilution_sum", self.dilution_sum),
        ):
            if not isinstance(value, Fraction):
                raise TypeError(f"{name} must be an exact Fraction")

        status_total = (
            self.settled_round_count
            + self.rejected_round_count
            + self.unincluded_round_count
            + self.missing_outcome_round_count
        )
        if status_total != self.economically_processed_round_count:
            raise ValueError("round status counts must equal processed rounds")
        provenance_total = (
            self.observed_outcome_count
            + self.enriched_outcome_count
            + self.missing_outcome_count
        )
        if provenance_total != self.economically_processed_round_count:
            raise ValueError("provenance counts must equal processed rounds")
        if self.missing_outcome_count != self.missing_outcome_round_count:
            raise ValueError("missing outcome counts must agree")
        if self.total_returned_sol_lamports != (
            self.total_returned_principal_lamports
            + self.total_sol_winnings_lamports
        ):
            raise ValueError("returned SOL components are inconsistent")
        if self.total_returned_sol_lamports != (
            self.total_gross_sol_inflow_lamports
        ):
            raise ValueError("returned SOL must equal gross SOL inflow")
        if self.net_sol_change_lamports != (
            self.total_gross_sol_inflow_lamports
            - self.total_gross_sol_outflow_lamports
        ):
            raise ValueError("net SOL change is inconsistent")
        if self.total_gross_sol_outflow_lamports != (
            self.total_deployed_lamports
            + self.total_transaction_fees_lamports
            + self.total_priority_fees_lamports
            + self.total_checkpoint_costs_lamports
        ):
            raise ValueError("gross SOL outflow components are inconsistent")
        if self.total_deployed_lamports > (
            self.total_deployment_budget_lamports
        ):
            raise ValueError("deployed lamports exceed aggregate budget")
        if self.maximum_concurrent_sol_exposure_lamports > (
            self.total_deployed_lamports
        ):
            raise ValueError("maximum exposure exceeds total deployment")
        if self.scenario_identity is None and self.economically_processed_round_count:
            raise ValueError("processed metrics require a scenario identity")
        if self.protocol_revision is None and self.economically_processed_round_count:
            raise ValueError("processed metrics require a protocol revision")
        if self.solo_reward_round_count + self.split_reward_round_count > (
            self.settled_round_count
        ):
            raise ValueError("reward treatment counts exceed settled rounds")
        for name, value in (
            (
                "winning_square_capital_share_sum",
                self.winning_square_capital_share_sum,
            ),
            ("dilution_sum", self.dilution_sum),
        ):
            if not 0 <= value <= self.settled_round_count:
                raise ValueError(f"{name} is inconsistent with settled rounds")

        object.__setattr__(
            self,
            "metrics_identity",
            _identity(
                "rfc011-economic-experiment-metrics-sha256",
                self._identity_payload(),
            ),
        )

    @property
    def provenance_summary(self) -> tuple[tuple[str, int], ...]:
        """Return canonical outcome-provenance counts."""

        return (
            ("observed", self.observed_outcome_count),
            ("enriched", self.enriched_outcome_count),
            ("missing", self.missing_outcome_count),
        )

    @property
    def mean_deployed_lamports(self) -> Fraction | None:
        return _ratio_or_none(
            self.total_deployed_lamports,
            self.settled_round_count,
        )

    @property
    def deployment_budget_utilization(self) -> Fraction | None:
        return _ratio_or_none(
            self.total_deployed_lamports,
            self.total_deployment_budget_lamports,
        )

    @property
    def mean_ore_earned_raw(self) -> Fraction | None:
        return _ratio_or_none(
            self.total_ore_earned_raw,
            self.settled_round_count,
        )

    @property
    def ore_per_sol_deployed(self) -> Fraction | None:
        return _ratio_or_none(
            self.total_ore_earned_raw,
            self.total_deployed_lamports,
        )

    @property
    def solo_reward_frequency(self) -> Fraction | None:
        return _ratio_or_none(
            self.solo_reward_round_count,
            self.settled_round_count,
        )

    @property
    def split_reward_frequency(self) -> Fraction | None:
        return _ratio_or_none(
            self.split_reward_round_count,
            self.settled_round_count,
        )

    @property
    def mean_winning_square_capital_share(self) -> Fraction | None:
        return _ratio_or_none(
            self.winning_square_capital_share_sum,
            self.settled_round_count,
        )

    @property
    def mean_dilution(self) -> Fraction | None:
        return _ratio_or_none(
            self.dilution_sum,
            self.settled_round_count,
        )

    @property
    def capture_efficiency(self) -> Fraction | None:
        return _ratio_or_none(
            self.capture_efficiency_ore_raw_numerator,
            self.capture_efficiency_deployed_lamports_denominator,
        )

    @property
    def net_sol_return_rate(self) -> Fraction | None:
        return _ratio_or_none(
            self.net_sol_change_lamports,
            self.total_gross_sol_outflow_lamports,
        )

    @property
    def completeness_percentage(self) -> Fraction | None:
        return _ratio_or_none(
            (self.observed_outcome_count + self.enriched_outcome_count) * 100,
            self.economically_processed_round_count,
        )

    def _identity_payload(self) -> dict[str, Any]:
        return {
            name: _plain_metric_value(value)
            for name, value in (
                (field_name, getattr(self, field_name))
                for field_name in self.__dataclass_fields__
                if field_name != "metrics_identity"
            )
        }


@dataclass(frozen=True, slots=True)
class EconomicMetricsEngine:
    """Aggregate only ordered immutable EconomicRoundResult evidence."""

    model_identity: str

    def __post_init__(self) -> None:
        _validate_identity("model_identity", self.model_identity)

    def aggregate(
        self,
        results: tuple[EconomicRoundResult, ...],
    ) -> EconomicExperimentMetrics:
        """Return exact experiment-level metrics without recomputing rounds."""

        completed = _validated_results(results)
        settled = tuple(
            value
            for value in completed
            if value.status is EconomicRoundStatus.SETTLED
        )
        processed_count = len(completed)
        settled_count = len(settled)
        total_deployed = sum(value.deployed_sol_lamports for value in settled)
        total_principal = sum(
            value.returned_principal_lamports for value in settled
        )
        total_winnings = sum(value.sol_winnings_lamports for value in settled)
        gross_outflow = sum(
            value.gross_sol_outflow_lamports for value in settled
        )
        gross_inflow = sum(
            value.gross_sol_inflow_lamports for value in settled
        )
        total_ore = sum(value.ore_earned_raw for value in settled)
        total_budget = sum(
            value.deployment_budget_lamports for value in settled
        )
        winning_shares = tuple(
            _zero_safe_fraction(
                value.participant_winning_square_lamports,
                value.counterfactual_winning_square_lamports,
            )
            for value in settled
        )
        dilutions = tuple(
            _zero_safe_fraction(
                value.dilution_numerator_lamports,
                value.dilution_denominator_lamports,
            )
            for value in settled
        )
        observed = sum(value.outcome_source == "observed" for value in completed)
        enriched = sum(value.outcome_source == "enriched" for value in completed)
        missing = sum(
            value.status is EconomicRoundStatus.MISSING_OUTCOME
            for value in completed
        )

        return EconomicExperimentMetrics(
            metrics_engine_identity=self.model_identity,
            scenario_identity=(completed[0].scenario_identity if completed else None),
            protocol_revision=(completed[0].protocol_revision if completed else None),
            economically_processed_round_count=processed_count,
            settled_round_count=settled_count,
            rejected_round_count=sum(
                value.status is EconomicRoundStatus.REJECTED
                for value in completed
            ),
            unincluded_round_count=sum(
                value.status is EconomicRoundStatus.UNINCLUDED
                for value in completed
            ),
            missing_outcome_round_count=missing,
            total_deployed_lamports=total_deployed,
            total_deployment_budget_lamports=total_budget,
            total_returned_principal_lamports=total_principal,
            total_sol_winnings_lamports=total_winnings,
            total_returned_sol_lamports=total_principal + total_winnings,
            total_protocol_fees_lamports=sum(
                value.protocol_deductions_lamports for value in settled
            ),
            total_transaction_fees_lamports=sum(
                value.transaction_fees_lamports for value in settled
            ),
            total_priority_fees_lamports=sum(
                value.priority_fees_lamports for value in settled
            ),
            total_checkpoint_costs_lamports=sum(
                value.checkpoint_costs_lamports for value in settled
            ),
            total_gross_sol_outflow_lamports=gross_outflow,
            total_gross_sol_inflow_lamports=gross_inflow,
            net_sol_change_lamports=gross_inflow - gross_outflow,
            maximum_concurrent_sol_exposure_lamports=max(
                (value.deployed_sol_lamports for value in settled),
                default=0,
            ),
            total_ore_earned_raw=total_ore,
            solo_reward_round_count=sum(
                value.reward_treatment is ORERewardTreatment.SOLO
                for value in settled
            ),
            split_reward_round_count=sum(
                value.reward_treatment is ORERewardTreatment.SPLIT
                for value in settled
            ),
            winning_square_capital_share_sum=sum(
                winning_shares,
                start=Fraction(0, 1),
            ),
            dilution_sum=sum(
                dilutions,
                start=Fraction(0, 1),
            ),
            capture_efficiency_ore_raw_numerator=sum(
                value.capture_efficiency_ore_raw_numerator
                for value in settled
            ),
            capture_efficiency_deployed_lamports_denominator=sum(
                value.capture_efficiency_deployed_lamports_denominator
                for value in settled
            ),
            observed_outcome_count=observed,
            enriched_outcome_count=enriched,
            missing_outcome_count=missing,
        )


def _validated_results(
    results: tuple[EconomicRoundResult, ...],
) -> tuple[EconomicRoundResult, ...]:
    if not isinstance(results, tuple) or not all(
        isinstance(value, EconomicRoundResult) for value in results
    ):
        raise TypeError(
            "results must be an immutable EconomicRoundResult tuple"
        )
    identities = tuple(value.result_identity for value in results)
    if len(set(identities)) != len(identities):
        raise ValueError("economic result identities must be unique")
    round_identifiers = tuple(value.round_identifier for value in results)
    if any(value is None for value in round_identifiers):
        raise ValueError("runner results must identify every replay round")
    if len(set(round_identifiers)) != len(round_identifiers):
        raise ValueError("economic result round identities must be unique")
    if len({value.scenario_identity for value in results}) > 1:
        raise ValueError("economic results must share one scenario identity")
    if len({value.protocol_revision for value in results}) > 1:
        raise ValueError("economic results must share one protocol revision")
    for index, value in enumerate(results):
        try:
            identity_matches = replace(value).result_identity == value.result_identity
        except (TypeError, ValueError):
            identity_matches = False
        if not identity_matches:
            raise ValueError("economic result identity is inconsistent")
        if value.status is EconomicRoundStatus.MISSING_OUTCOME:
            if value.outcome_source is not None:
                raise ValueError("missing outcomes cannot claim provenance")
            if index != len(results) - 1:
                raise ValueError("a missing outcome must terminate its interval")
        elif value.outcome_source not in {"observed", "enriched"}:
            raise ValueError(
                "processed outcomes require observed or enriched provenance"
            )
    return results


def _ratio_or_none(
    numerator: int | Fraction,
    denominator: int,
) -> Fraction | None:
    if denominator == 0:
        if numerator != 0:
            raise ValueError("a nonzero metric cannot have a zero denominator")
        return None
    return Fraction(numerator, denominator)


def _zero_safe_fraction(numerator: int, denominator: int) -> Fraction:
    if denominator == 0:
        if numerator != 0:
            raise ValueError("a nonzero share cannot have a zero denominator")
        return Fraction(0, 1)
    return Fraction(numerator, denominator)


def _plain_metric_value(value: Any) -> Any:
    if isinstance(value, Fraction):
        return {
            "denominator": value.denominator,
            "numerator": value.numerator,
        }
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


__all__ = ("EconomicExperimentMetrics", "EconomicMetricsEngine")
