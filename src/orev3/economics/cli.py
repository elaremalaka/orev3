from __future__ import annotations

import argparse
import json
import platform
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from orev3.economics.aggregation import (
    economic_metrics,
    longest_losing_streak,
    segment_frames,
)
from orev3.economics.bootstrap import (
    paired_round_bootstrap,
    round_bootstrap_interval,
)
from orev3.economics.reporting import (
    ensure_outputs_available,
    output_paths,
    write_outputs,
)
from orev3.economics.schemas import (
    EconomicAssumptions,
    FinalRoundEconomics,
    json_safe,
)
from orev3.economics.simulator import (
    REQUIRED_HEURISTICS,
    attach_outcomes,
    extract_strategy_rank_summaries,
    random_rank_summary,
    reference_opportunity_output,
    simulate_bankroll,
    simulate_scenario,
    strategy_definitions,
)
from orev3.economics.validation import validate_canonical_inputs
from orev3.replay.loader import load_round_index


DEFAULT_DATASET = Path("data/research/square_feature_dataset_v1.csv")
DEFAULT_MANIFEST = Path(
    "data/research/square_feature_dataset_v1.manifest.json"
)
DEFAULT_FEATURE_SETS = Path("data/research/baseline_feature_sets_v1.json")
DEFAULT_PREDICTIONS = Path("data/research/baseline_predictions_v1.csv")
DEFAULT_LIFECYCLES = Path("data/derived/round_lifecycles_v1.jsonl")
DEFAULT_ASSUMPTIONS = Path(
    "config/economics/rfc005_assumptions_v1.json"
)
DEFAULT_RESULTS_DIR = Path("data/research")


def load_final_round_economics(
    path: Path,
) -> dict[int, FinalRoundEconomics]:
    index = load_round_index(path)
    outcomes: dict[int, FinalRoundEconomics] = {}
    for round_id in sorted(index):
        lifecycle = index[round_id]
        finalized = lifecycle.finalized_outcome
        if finalized is None:
            continue
        if finalized.winning_square is None:
            continue
        outcome = FinalRoundEconomics(
            round_id=round_id,
            outcome_source=str(lifecycle.finalized_outcome_source),
            winning_square=int(finalized.winning_square),
            winning_square_deployed_lamports=int(
                finalized.deployed_lamports[finalized.winning_square]
            ),
            total_winnings_lamports=int(finalized.total_winnings),
            total_vaulted_lamports=int(finalized.total_vaulted),
            total_deployed_lamports=int(sum(finalized.deployed_lamports)),
            round_motherlode_raw=int(finalized.round_motherlode),
        )
        outcome.validate()
        outcomes[round_id] = outcome
    return outcomes


def _metric_rows(
    frame: pd.DataFrame,
    *,
    strategy: str,
    square_count: int,
    allocation_rule: str,
    deployment_lamports: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for segment, value, subset in segment_frames(frame):
        rows.append(
            {
                "strategy": strategy,
                "square_count": square_count,
                "allocation_rule": allocation_rule,
                "deployment_lamports": deployment_lamports,
                "segment": segment,
                "segment_value": value,
                **economic_metrics(subset),
            }
        )
    return rows


def _reference_scenario(
    frame: pd.DataFrame,
    *,
    strategy: str,
    assumptions: EconomicAssumptions,
) -> pd.DataFrame:
    return simulate_scenario(
        frame,
        strategy=strategy,
        square_count=assumptions.reference_square_count,
        allocation_rule=assumptions.reference_allocation_rule,
        deployment_lamports=assumptions.reference_deployment_lamports,
        assumptions=assumptions,
    )


def _price_scenarios(
    reference: dict[str, pd.DataFrame],
    assumptions: EconomicAssumptions,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for strategy, frame in sorted(reference.items()):
        metrics = economic_metrics(frame)
        net_sol = (
            metrics["net_sol_after_fees_lamports"]
            / assumptions.lamports_per_sol
        )
        deployed_sol = (
            metrics["total_sol_deployed_lamports"]
            / assumptions.lamports_per_sol
        )
        ore = metrics["total_ore_earned"]
        for sol_price in assumptions.sol_price_usd_scenarios:
            for ore_price in assumptions.ore_price_usd_scenarios:
                combined = net_sol * sol_price + ore * ore_price
                capital_usd = deployed_sol * sol_price
                rows.append(
                    {
                        "strategy": strategy,
                        "sol_price_usd": sol_price,
                        "ore_price_usd": ore_price,
                        "ore_marked_value_usd": ore * ore_price,
                        "combined_net_usd": combined,
                        "combined_roi": (
                            combined / capital_usd if capital_usd else None
                        ),
                        "break_even_ore_price_usd": (
                            (-net_sol * sol_price / ore)
                            if ore > 0 and net_sol < 0
                            else None
                        ),
                        "scope": (
                            "hypothetical_motherlode_only_ore_"
                            "base_ore_unavailable"
                        ),
                    }
                )
    return rows


def _bankroll_summary(paths: pd.DataFrame) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for (strategy, starting), group in paths.groupby(
        ["strategy", "starting_bankroll_lamports"], sort=True
    ):
        records.append(
            {
                "strategy": strategy,
                "starting_bankroll_lamports": int(starting),
                "ending_bankroll_lamports": int(
                    group["bankroll_after_lamports"].iloc[-1]
                ),
                "maximum_drawdown_lamports": int(
                    group["drawdown_lamports"].max()
                ),
                "participation_rate": float(group["participated"].mean()),
                "longest_losing_streak": longest_losing_streak(
                    group["net_sol_after_fees_lamports"].to_numpy(
                        dtype=np.int64
                    )
                ),
                "ore_earned": float(group["ore_earned"].sum()),
                "ruined": bool(
                    group["participated"].any()
                    and not group["participated"].iloc[-1]
                ),
            }
        )
    return records


def run_canonical_simulation(
    *,
    dataset_path: Path,
    manifest_path: Path,
    feature_sets_path: Path,
    predictions_path: Path,
    lifecycles_path: Path,
    assumptions_path: Path,
    results_dir: Path,
    force: bool,
    validation_only: bool,
) -> dict[str, Any]:
    started = time.perf_counter()
    print("Loading RFC-004 out-of-sample predictions...")
    predictions = pd.read_csv(predictions_path, low_memory=False)
    validation = validate_canonical_inputs(
        dataset_path=dataset_path,
        manifest_path=manifest_path,
        feature_sets_path=feature_sets_path,
        predictions=predictions,
    )
    assumptions = EconomicAssumptions.from_path(assumptions_path)
    outcomes = load_final_round_economics(lifecycles_path)
    if len(outcomes) != 439:
        raise ValueError(
            f"Expected 439 finalized economic outcomes, got {len(outcomes)}"
        )
    summaries = extract_strategy_rank_summaries(predictions)
    definitions = strategy_definitions()
    if validation_only:
        return {
            "validation_only": True,
            "validation": validation,
            "economic_outcomes": len(outcomes),
            "strategies": len(summaries),
        }

    paths = output_paths(results_dir)
    ensure_outputs_available(paths, force=force)
    print("Simulating fixed strategy and deployment scenarios...")
    metric_rows: list[dict[str, Any]] = []
    reference_results: dict[str, pd.DataFrame] = {}
    opportunity_frames: list[pd.DataFrame] = []
    for strategy, summary in sorted(summaries.items()):
        attached = attach_outcomes(summary, outcomes)
        for square_count in assumptions.square_counts:
            for allocation_rule in assumptions.allocation_rules:
                for deployment in assumptions.deployment_lamports:
                    simulated = simulate_scenario(
                        attached,
                        strategy=strategy,
                        square_count=square_count,
                        allocation_rule=allocation_rule,
                        deployment_lamports=deployment,
                        assumptions=assumptions,
                    )
                    metric_rows.extend(
                        _metric_rows(
                            simulated,
                            strategy=strategy,
                            square_count=square_count,
                            allocation_rule=allocation_rule,
                            deployment_lamports=deployment,
                        )
                    )
                    if (
                        square_count == assumptions.reference_square_count
                        and allocation_rule
                        == assumptions.reference_allocation_rule
                        and deployment
                        == assumptions.reference_deployment_lamports
                    ):
                        reference_results[strategy] = simulated
                        opportunity_frames.append(
                            reference_opportunity_output(simulated)
                        )
    metrics = pd.DataFrame(metric_rows).sort_values(
        [
            "strategy",
            "square_count",
            "allocation_rule",
            "deployment_lamports",
            "segment",
            "segment_value",
        ],
        kind="stable",
    )
    opportunities = pd.concat(opportunity_frames, ignore_index=True).sort_values(
        ["strategy", "round_id", "observation_index"], kind="stable"
    )

    print("Evaluating deterministic random-seed distribution...")
    base = next(iter(summaries.values()))
    random_distribution: list[dict[str, Any]] = []
    for offset in range(assumptions.random_seed_count):
        seed = assumptions.random_seed + offset
        random_summary = random_rank_summary(base, seed)
        simulated = _reference_scenario(
            attach_outcomes(random_summary, outcomes),
            strategy=f"random_seed_{seed}",
            assumptions=assumptions,
        )
        random_distribution.append(
            {"seed": seed, **economic_metrics(simulated)}
        )

    reference_metrics = {
        strategy: economic_metrics(frame)
        for strategy, frame in reference_results.items()
    }
    heuristic_validation = {
        strategy: economic_metrics(
            reference_results[strategy].loc[
                reference_results[strategy]["split_kind"].eq("validation")
            ]
        )["net_sol_after_fees_lamports"]
        for strategy in REQUIRED_HEURISTICS
    }
    best_heuristic = max(
        sorted(heuristic_validation),
        key=heuristic_validation.__getitem__,
    )

    print("Computing round-aware paired uncertainty...")
    comparisons = {
        "seeded_random": "seeded_random_20260725",
        "least_miner": "least_miner_count",
        "least_deployed": "least_deployed",
        "least_crowded": "existing_least_crowded",
        "validation_selected_best_heuristic": best_heuristic,
    }
    bootstrap_rows: list[dict[str, Any]] = []
    for strategy, candidate in sorted(reference_results.items()):
        for baseline_label, baseline_name in comparisons.items():
            interval = paired_round_bootstrap(
                candidate,
                reference_results[baseline_name],
                seed=assumptions.bootstrap_seed,
                samples=assumptions.bootstrap_samples,
            )
            bootstrap_rows.append(
                {
                    "strategy": strategy,
                    "baseline": baseline_name,
                    "baseline_role": baseline_label,
                    "square_count": assumptions.reference_square_count,
                    "allocation_rule": assumptions.reference_allocation_rule,
                    "deployment_lamports": (
                        assumptions.reference_deployment_lamports
                    ),
                    **interval,
                }
            )
    bootstrap = pd.DataFrame(bootstrap_rows).sort_values(
        ["strategy", "baseline_role"], kind="stable"
    )

    print("Simulating fixed-bankroll reference paths...")
    bankroll_frames: list[pd.DataFrame] = []
    for strategy, frame in sorted(reference_results.items()):
        for bankroll in assumptions.starting_bankroll_lamports:
            bankroll_frames.append(
                simulate_bankroll(
                    frame,
                    starting_bankroll_lamports=bankroll,
                    assumptions=assumptions,
                )
            )
    bankroll_paths = pd.concat(bankroll_frames, ignore_index=True).sort_values(
        [
            "strategy",
            "starting_bankroll_lamports",
            "round_id",
            "observation_index",
        ],
        kind="stable",
    )

    sources = pd.Series(
        [outcome.outcome_source for outcome in outcomes.values()]
    ).value_counts()
    oos_round_ids = set(int(value) for value in predictions["round_id"].unique())
    oos_outcomes = [
        outcome for round_id, outcome in outcomes.items()
        if round_id in oos_round_ids
    ]
    oos_sources = pd.Series(
        [outcome.outcome_source for outcome in oos_outcomes]
    ).value_counts()
    motherlodes = sum(
        outcome.round_motherlode_raw > 0 for outcome in outcomes.values()
    )
    oos_motherlodes = sum(
        outcome.round_motherlode_raw > 0 for outcome in oos_outcomes
    )
    results = {
        "schema_version": 1,
        "experiment": "RFC-005 leakage-safe economic simulation",
        "branch_scope": "research_only_no_live_deployment",
        "validation": validation,
        "accounting": {
            "primary_realized_wallet": {
                "eligible_opportunities": 0,
                "excluded_opportunities": 13_652,
                "exclusion_reason": "missing_participant_wallet_accounting",
                "conclusion": "historical realized wallet economics unavailable",
            },
            "secondary_reconstructed": {
                "mode": assumptions.accounting_mode,
                "eligible_opportunities": 13_652,
                "price_taking": True,
                "counterfactual_denominator": False,
                "sol_return_equation": (
                    "winner allocation / recorded final winning-square "
                    "deployment * finalized total_winnings"
                ),
                "ore_equation": (
                    "same proportional share of round_motherlode only"
                ),
                "base_ore_available": False,
            },
        },
        "economic_data_coverage": {
            "rounds": len(outcomes),
            "observed_rounds": int(sources.get("observed", 0)),
            "enriched_rounds": int(sources.get("enriched", 0)),
            "rounds_with_total_winnings": sum(
                value.total_winnings_lamports > 0
                for value in outcomes.values()
            ),
            "rounds_with_winning_denominator": sum(
                value.winning_square_deployed_lamports > 0
                for value in outcomes.values()
            ),
            "motherlode_rounds": motherlodes,
            "oos_rounds": len(oos_outcomes),
            "oos_opportunities": 13_652,
            "oos_observed_rounds": int(oos_sources.get("observed", 0)),
            "oos_enriched_rounds": int(oos_sources.get("enriched", 0)),
            "oos_motherlode_rounds": oos_motherlodes,
            "participant_wallet_records": 0,
            "observed_fee_records": 0,
        },
        "artifact_limitations": {
            "model_top_k_square_identities": "unavailable_beyond_top_1",
            "top_k_economic_evaluation": (
                "supported from persisted true-winner rank"
            ),
            "rank_ensembles": "excluded_missing_full_rank_vectors",
        },
        "holdout_policy": (
            "report-only; all strategies, scenarios, fees, and definitions "
            "come from the tracked assumptions file before holdout reporting"
        ),
        "validation_selected_best_fixed_heuristic": best_heuristic,
        "reference_scenario": {
            "deployment_lamports": assumptions.reference_deployment_lamports,
            "square_count": assumptions.reference_square_count,
            "allocation_rule": assumptions.reference_allocation_rule,
        },
        "reference_metrics": reference_metrics,
        "random_seed_distribution": random_distribution,
        "paired_bootstrap": bootstrap.to_dict(orient="records"),
        "price_scenarios": _price_scenarios(
            reference_results, assumptions
        ),
        "bankroll_summary": _bankroll_summary(bankroll_paths),
        "reproducibility": {
            "random_seed": assumptions.random_seed,
            "bootstrap_seed": assumptions.bootstrap_seed,
            "deterministic_integer_accounting": True,
            "floating_tolerance": 1e-12,
        },
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
        },
        "runtime_seconds": time.perf_counter() - started,
    }
    assumption_output = {
        "schema_version": 1,
        **assumptions.as_dict(),
        "provenance": {
            "deployment_grid": "prespecified RFC-005 request",
            "fees": "assumption; repository has no observed transaction fees",
            "reward_accounting": (
                "reconstructed from finalized protocol totals; not wallet realized"
            ),
            "ore": "round Motherlode only; base ORE unavailable",
        },
    }
    write_outputs(
        paths=paths,
        results=json_safe(results),
        metrics=metrics,
        opportunities=opportunities,
        bankroll=bankroll_paths,
        assumptions=assumption_output,
        strategies=definitions,
        bootstrap=bootstrap,
    )
    print(
        f"Wrote {len(paths)} outputs to {results_dir}; "
        f"runtime={results['runtime_seconds']:.3f}s"
    )
    return results


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run RFC-005 leakage-safe economic simulation."
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--feature-sets", type=Path, default=DEFAULT_FEATURE_SETS
    )
    parser.add_argument(
        "--predictions", type=Path, default=DEFAULT_PREDICTIONS
    )
    parser.add_argument("--lifecycles", type=Path, default=DEFAULT_LIFECYCLES)
    parser.add_argument(
        "--assumptions", type=Path, default=DEFAULT_ASSUMPTIONS
    )
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--validation-only", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.seed is not None:
        configured = EconomicAssumptions.from_path(args.assumptions).random_seed
        if args.seed != configured:
            raise ValueError(
                f"--seed must match frozen assumptions seed {configured}"
            )
    result = run_canonical_simulation(
        dataset_path=args.dataset,
        manifest_path=args.manifest,
        feature_sets_path=args.feature_sets,
        predictions_path=args.predictions,
        lifecycles_path=args.lifecycles,
        assumptions_path=args.assumptions,
        results_dir=args.results_dir,
        force=args.force,
        validation_only=args.validation_only,
    )
    print(
        json.dumps(
            json_safe(
                {
                    "validation_only": result.get(
                        "validation_only", False
                    ),
                    "dataset_sha256": result.get(
                        "validation", {}
                    ).get("dataset_sha256"),
                    "economic_outcomes": result.get(
                        "economic_outcomes",
                        result.get("economic_data_coverage", {}).get("rounds"),
                    ),
                    "runtime_seconds": result.get("runtime_seconds"),
                }
            ),
            sort_keys=True,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
