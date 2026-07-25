from __future__ import annotations

import pandas as pd
import pytest

from orev3.economics.schemas import (
    EconomicAssumptions,
    FinalRoundEconomics,
)


@pytest.fixture
def assumptions() -> EconomicAssumptions:
    return EconomicAssumptions(
        accounting_mode="historical_price_taking_reconstructed",
        lamports_per_sol=1_000_000_000,
        ore_raw_per_ore=100_000_000_000,
        deployment_lamports=(1_000_000,),
        square_counts=(1, 2, 3, 4, 5),
        allocation_rules=("equal", "rank_decay"),
        deploy_fee_lamports=5_000,
        claim_fee_lamports=5_000,
        priority_fee_lamports=0,
        failed_transaction_cost_lamports=0,
        claim_batch_size=1,
        claim_timing="immediate_after_positive_return_or_ore",
        random_seed=42,
        random_seed_count=2,
        bootstrap_seed=43,
        bootstrap_samples=100,
        reference_deployment_lamports=1_000_000,
        reference_square_count=1,
        reference_allocation_rule="equal",
        starting_bankroll_lamports=(100_000_000,),
        insufficient_bankroll_rule="skip",
        sol_price_usd_scenarios=(100.0,),
        ore_price_usd_scenarios=(1.0,),
        fee_provenance="assumption",
        ore_scope="motherlode_only",
        principal_treatment="deployment_is_cost",
    )


@pytest.fixture
def outcome() -> FinalRoundEconomics:
    return FinalRoundEconomics(
        round_id=1,
        outcome_source="observed",
        winning_square=3,
        winning_square_deployed_lamports=100_000_000,
        total_winnings_lamports=1_000_000_000,
        total_vaulted_lamports=100_000_000,
        total_deployed_lamports=1_200_000_000,
        round_motherlode_raw=10_000_000_000_000,
    )


@pytest.fixture
def simulated_frame() -> pd.DataFrame:
    rows = []
    for index, net in enumerate((-100, -100, 300, -100)):
        rows.append(
            {
                "round_id": 10 + index // 2,
                "observation_index": index,
                "fold": "validation_1",
                "split_kind": "validation",
                "outcome_source": "observed" if index < 2 else "enriched",
                "strategy": "test",
                "feature_set": "all_72",
                "square_count": 1,
                "allocation_rule": "equal",
                "deployment_lamports": 1000,
                "participated": True,
                "winner_hit": net > 0,
                "gross_sol_return_lamports": net + 1000,
                "net_sol_before_fees_lamports": net,
                "deploy_cost_lamports": 5,
                "claim_cost_lamports": 0,
                "transaction_cost_lamports": 5,
                "net_sol_after_deploy_lamports": net - 5,
                "net_sol_after_fees_lamports": net - 5,
                "ore_earned": 1.0 if net > 0 else 0.0,
                "motherlode": net > 0,
            }
        )
    return pd.DataFrame(rows)
