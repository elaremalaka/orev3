from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


LAMPORTS_PER_SOL = 1_000_000_000


@dataclass(frozen=True, slots=True)
class EconomicAssumptions:
    accounting_mode: str
    lamports_per_sol: int
    ore_raw_per_ore: int
    deployment_lamports: tuple[int, ...]
    square_counts: tuple[int, ...]
    allocation_rules: tuple[str, ...]
    deploy_fee_lamports: int
    claim_fee_lamports: int
    priority_fee_lamports: int
    failed_transaction_cost_lamports: int
    claim_batch_size: int
    claim_timing: str
    random_seed: int
    random_seed_count: int
    bootstrap_seed: int
    bootstrap_samples: int
    reference_deployment_lamports: int
    reference_square_count: int
    reference_allocation_rule: str
    starting_bankroll_lamports: tuple[int, ...]
    insufficient_bankroll_rule: str
    sol_price_usd_scenarios: tuple[float, ...]
    ore_price_usd_scenarios: tuple[float, ...]
    fee_provenance: str
    ore_scope: str
    principal_treatment: str

    @classmethod
    def from_path(cls, path: Path) -> "EconomicAssumptions":
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw.pop("schema_version", None)
        for key in (
            "deployment_lamports",
            "square_counts",
            "allocation_rules",
            "starting_bankroll_lamports",
            "sol_price_usd_scenarios",
            "ore_price_usd_scenarios",
        ):
            raw[key] = tuple(raw[key])
        result = cls(**raw)
        result.validate()
        return result

    def validate(self) -> None:
        if self.accounting_mode != "historical_price_taking_reconstructed":
            raise ValueError("Unsupported accounting mode")
        if self.lamports_per_sol <= 0 or self.ore_raw_per_ore <= 0:
            raise ValueError("Unit conversions must be positive")
        if not self.deployment_lamports or any(
            value < 0 for value in self.deployment_lamports
        ):
            raise ValueError("Deployment scenarios must be non-negative")
        if set(self.square_counts) - {1, 2, 3, 4, 5}:
            raise ValueError("Square counts must be in 1..5")
        if set(self.allocation_rules) - {"equal", "rank_decay"}:
            raise ValueError("Unsupported allocation rule")
        fees = (
            self.deploy_fee_lamports,
            self.claim_fee_lamports,
            self.priority_fee_lamports,
            self.failed_transaction_cost_lamports,
        )
        if any(value < 0 for value in fees):
            raise ValueError("Fees must be non-negative")
        if self.random_seed_count < 1 or self.bootstrap_samples < 1:
            raise ValueError("Seed and bootstrap counts must be positive")
        prices = (
            *self.sol_price_usd_scenarios,
            *self.ore_price_usd_scenarios,
        )
        if any(not math.isfinite(value) or value < 0 for value in prices):
            raise ValueError("Price scenarios must be finite and non-negative")
        if self.reference_deployment_lamports not in self.deployment_lamports:
            raise ValueError("Reference deployment must be in the scenario grid")
        if self.reference_square_count not in self.square_counts:
            raise ValueError("Reference square count must be in the scenario grid")
        if self.reference_allocation_rule not in self.allocation_rules:
            raise ValueError("Reference allocation must be in the scenario grid")

    def as_dict(self) -> dict[str, Any]:
        return {
            key: list(value) if isinstance(value, tuple) else value
            for key, value in asdict(self).items()
        }


@dataclass(frozen=True, slots=True)
class FinalRoundEconomics:
    round_id: int
    outcome_source: str
    winning_square: int
    winning_square_deployed_lamports: int
    total_winnings_lamports: int
    total_vaulted_lamports: int
    total_deployed_lamports: int
    round_motherlode_raw: int

    def validate(self) -> None:
        if self.outcome_source not in {"observed", "enriched"}:
            raise ValueError("Invalid outcome source")
        if not 0 <= self.winning_square < 25:
            raise ValueError("Invalid winning square")
        values = (
            self.winning_square_deployed_lamports,
            self.total_winnings_lamports,
            self.total_vaulted_lamports,
            self.total_deployed_lamports,
            self.round_motherlode_raw,
        )
        if any(not math.isfinite(value) or value < 0 for value in values):
            raise ValueError("Economic values must be non-negative")
        if self.winning_square_deployed_lamports <= 0:
            raise ValueError("Winning-square denominator is unavailable")


@dataclass(frozen=True, slots=True)
class AccountingResult:
    deployment_lamports: int
    gross_sol_return_lamports: int
    net_sol_before_fees_lamports: int
    deploy_cost_lamports: int
    claim_cost_lamports: int
    transaction_cost_lamports: int
    net_sol_after_deploy_lamports: int
    net_sol_after_fees_lamports: int
    ore_earned_raw: int
    ore_earned: float
    winner_hit: bool
    motherlode: bool


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if hasattr(value, "item"):
        return json_safe(value.item())
    return value
