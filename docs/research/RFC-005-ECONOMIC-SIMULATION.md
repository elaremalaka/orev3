# RFC-005 — Leakage-Safe Economic Simulation and Strategy Evaluation

## 1. Executive summary

RFC-005 implements a deterministic, chronological economic-simulation
framework over the RFC-004 out-of-sample predictions. It does not establish
realized historical wallet profitability because participant-level deposits,
receipts, fees, and ORE claims are absent from the repository.

The primary realized-wallet analysis therefore has zero eligible opportunities
and excludes all 13,652 out-of-sample opportunities with reason
`missing_participant_wallet_accounting`.

A secondary, explicitly reconstructed historical price-taking analysis finds
positive aggregate top-1 SOL results for the all-72 Random Forest and both
HistGradientBoosting configurations at several fixed deployment sizes.
However:

- performance is not directionally consistent across chronological folds;
- paired round-bootstrap intervals versus random and least-miner cross zero;
- directly observed and enriched outcomes differ materially;
- no Motherlode occurs in the 176 out-of-sample rounds;
- base ORE production is unavailable;
- the payout equation is reconstructed rather than wallet-verified; and
- fixed fees erase the reconstructed edge at the smallest deployment.

The evidence does not justify controlled live testing. The next gate should be
additional directly observed wallet/economic data collection plus continued
paper simulation.

## 2. Research question

The question is whether fixed model-ranked square selections improve separate
net SOL and ORE economics relative to deterministic random and existing
heuristics under explicit deployment, reward-sharing, and fee assumptions.

No probability is used for sizing, gating, or allocation.

## 3. Data sources

- Canonical 72-feature square dataset:
  `data/research/square_feature_dataset_v1.csv`
- Canonical manifest:
  `data/research/square_feature_dataset_v1.manifest.json`
- Frozen RFC-004 feature sets:
  `data/research/baseline_feature_sets_v1.json`
- RFC-004 OOS predictions:
  `data/research/baseline_predictions_v1.csv`
- Finalized lifecycle outcomes:
  `data/derived/round_lifecycles_v1.jsonl`
- Tracked assumptions:
  `config/economics/rfc005_assumptions_v1.json`

The canonical feature-dataset SHA-256 remains:

```text
9047141c99e2eb067bc0ca0bc5ee082ed141f91f16e25c23e125b062bf97983d
```

## 4. Economic-field completeness

All 439 rounds contain finalized winning square, winning-square deployment,
total winnings, total vaulted, and total deployed values. Outcome provenance
is 58 observed rounds and 381 enriched rounds.

The OOS sample contains:

- 176 rounds;
- 13,652 observation opportunities;
- 22 observed-outcome rounds;
- 154 enriched-outcome rounds;
- 1,713 observed-source opportunities;
- 11,939 enriched-source opportunities; and
- zero Motherlode rounds.

Unavailable fields are participant wallet deployment, wallet return, deploy
fee, claim fee, priority fee, failed transaction cost, claim record, base ORE
reward, and a verified participant-level payout equation.

## 5. Observed, reconstructed, and assumed values

Direct protocol values:

- finalized `total_winnings`;
- finalized `total_vaulted`;
- finalized per-square deployment;
- winning square;
- round Motherlode raw amount; and
- outcome source.

Reconstructed values:

- participant gross SOL return;
- participant net SOL;
- participant proportional Motherlode share; and
- bankroll path.

Configurable assumptions:

- deployment size;
- deploy and claim fees;
- allocation rule;
- claim timing and batch size;
- starting bankroll; and
- hypothetical SOL and ORE prices.

Unavailable values remain null or cause exclusion; they are not silently
imputed.

## 6. Simulation assumptions

The tracked assumptions file freezes all settings before holdout reporting.

Primary participation is every valid OOS opportunity. There are no
performance-derived gates. Insufficient sequential bankroll uses `skip`; it
never creates a negative balance.

The opportunity analysis treats each observation as an independent
counterfactual deployment opportunity. Multiple observations within one round
are alternatives sharing the same final outcome. Consequently, the optional
sequential bankroll path is a normalized stress diagnostic, not an executable
plan for repeatedly deploying into the same historical round.

## 7. Reward-sharing mechanics

The implemented secondary mode is:

```text
historical_price_taking_reconstructed
```

For a selected winning rank:

```text
gross SOL return =
    allocated lamports at winning rank
    / recorded final winning-square deployed lamports
    × finalized total_winnings
```

Integer division rounds down. Deployment is treated as cost; `total_winnings`
is treated as the gross return pool. The strategy does not alter other miners
or the recorded denominator.

No counterfactual-denominator mode is implemented because the repository does
not establish how an added deployment changes total winnings, vaulted SOL, or
ORE distribution.

## 8. ORE and Motherlode accounting

The repository does not support assigning the 25-value reward array to board
squares. Base ORE is therefore unavailable.

Only round Motherlode raw units are eligible for the reconstructed proportional
share, using `100,000,000,000` raw units per ORE. The archive has one
Motherlode round, but it occurs before the RFC-004 OOS blocks. OOS ORE is zero
for every strategy and scenario.

ORE-per-SOL, Motherlode dependence, and break-even ORE price cannot be
credibly estimated from this OOS sample.

## 9. Fee assumptions

No historical fee records are available. RFC-005 uses:

- deploy fee: 5,000 lamports per participating opportunity;
- claim fee: 5,000 lamports after a positive SOL return or ORE reward;
- priority fee: 0;
- failed-transaction cost: 0;
- claim batch size: 1; and
- claim timing: immediately after positive return or ORE.

Outputs preserve before-fee, after-deploy-cost, and after-all-fee values.

## 10. Chronological evaluation

RFC-004 boundaries are unchanged:

| Block | Training rounds | OOS rounds |
|---|---:|---:|
| validation_1 | 263 | 342395–342438 (44) |
| validation_2 | 307 | 342439–342482 (44) |
| validation_3 | 351 | 342483–342526 (44) |
| final_holdout | 395 | 342527–342570 (44) |

The holdout is report-only. Strategy membership, scenario grids, fees,
allocation, metrics, and reporting definitions are frozen in tracked code or
the assumptions file. The validation-selected fixed heuristic is
`highest_reward`; holdout results did not influence that choice.

## 11. Strategy definitions

Deployable persisted strategies:

- seeded random, seed `20260725`;
- least miner count;
- least deployed lamports;
- lowest miner share;
- highest reward signal;
- existing least-crowded ordering;
- Logistic Regression, all 72;
- Logistic Regression, conservative 52;
- Random Forest, all 72;
- Random Forest, conservative 52;
- HistGradientBoosting, all 72; and
- HistGradientBoosting, conservative 52.

Random variability uses 20 unselected deterministic seeds
`20260725`–`20260744`.

Equal-weight rank ensembles are implemented and tested, but the requested
model/heuristic ensembles are excluded from canonical evaluation because the
RFC-004 artifact persists only the top-1 selected identity and true winner's
rank, not each model's complete 25-square rank vector. Inventing missing
ranked-square identities would be invalid.

## 12. Square-count and allocation policies

Every strategy is evaluated at top-1 through top-5.

- Equal: equal lamports, with residual assigned from rank 1 upward.
- Rank decay: weights proportional to `1 / rank`, with deterministic residual
  assignment.

For models, top-k winner coverage and rank-dependent allocation are supported
from the persisted winner rank. Exact selected-square identities beyond top-1
remain unavailable. The opportunity-level artifact therefore reports the
exact top-1 reference scenario only.

## 13. Deployment sizes

Fixed total deployment scenarios:

| SOL | Lamports |
|---:|---:|
| 0.00005 | 50,000 |
| 0.00010 | 100,000 |
| 0.00025 | 250,000 |
| 0.00050 | 500,000 |
| 0.00100 | 1,000,000 |
| 0.00250 | 2,500,000 |
| 0.00500 | 5,000,000 |
| 0.01000 | 10,000,000 |

The reference scenario is 0.001 SOL, top-1, equal allocation.

## 14. Participation gates

The primary scenario participates in every valid OOS opportunity. No
data-mined gate or threshold is introduced. Participation is reported even
when bankroll constraints later force a skip.

## 15. Validation results

Reference scenario across the three validation blocks:

| Strategy | Winner hit | Net SOL after fees | ROI after fees |
|---|---:|---:|---:|
| Random Forest all-72 | 5.22% | +1.0539 SOL | +10.30% |
| HistGradientBoosting all-72 | 5.10% | +0.8900 SOL | +8.69% |
| HistGradientBoosting 52 | 5.10% | +0.8900 SOL | +8.69% |
| Random Forest 52 | 4.44% | -0.6397 SOL | -6.25% |
| Seeded random | 3.97% | -1.6172 SOL | -15.80% |
| Highest reward | 3.76% | -2.1852 SOL | -21.35% |
| Least deployed | 3.10% | -3.3122 SOL | -32.36% |
| Least miner / least crowded | 3.09% | -3.4926 SOL | -34.12% |
| Logistic all-72 | 2.54% | -4.8537 SOL | -47.42% |

These validation aggregates hide material fold instability.

## 16. Final holdout

Reference holdout:

| Strategy | Winner hit | Net SOL after fees | ROI after fees |
|---|---:|---:|---:|
| Highest reward | 9.07% | +3.0840 SOL | +90.28% |
| Least miner / least crowded | 7.23% | +1.9669 SOL | +57.58% |
| Logistic 52 | 4.98% | +0.1737 SOL | +5.08% |
| Logistic all-72 | 4.95% | +0.1575 SOL | +4.61% |
| HistGradientBoosting all-72 / 52 | 4.74% | +0.0814 SOL | +2.38% |
| Random Forest all-72 | 4.42% | -0.2075 SOL | -6.08% |
| Seeded random | 4.13% | -0.3842 SOL | -11.25% |
| Random Forest 52 | 1.96% | -1.9985 SOL | -58.50% |
| Least deployed | 1.67% | -2.1805 SOL | -63.83% |

The highest-reward ranking ties in this dataset and resolves by square index.
Its holdout result reflects the same late square-index concentration noted in
RFC-004, not usable reward signal.

## 17. Fold consistency

Reference after-fee ROI by block:

| Strategy | val_1 | val_2 | val_3 | holdout |
|---|---:|---:|---:|---:|
| Random Forest all-72 | -5.84% | -11.73% | +48.28% | -6.08% |
| HistGradientBoosting all-72 | -31.42% | +10.66% | +46.56% | +2.38% |
| Seeded random | -18.93% | -22.46% | -6.05% | -11.25% |
| Least miner | -17.23% | -7.11% | -77.81% | +57.58% |

Neither tree model demonstrates consistent positive economics.

## 18. Observed versus enriched outcomes

Reference source-separated results:

| Strategy | Observed ROI | Enriched ROI |
|---|---:|---:|
| HistGradientBoosting all-72 | +70.12% | -1.92% |
| Random Forest all-72 | +34.44% | +2.15% |
| Highest reward | -5.56% | +8.33% |
| Seeded random | -7.67% | -15.66% |
| Least miner | -46.93% | -6.05% |
| Logistic all-72 | -25.85% | -35.63% |

Only 22 OOS rounds are directly observed. The source differences are too large
and the observed sample too small for a source-invariant conclusion.

## 19. Random baseline distribution

Across 20 deterministic, unselected seeds in the reference scenario:

- mean net SOL: -1.9524 SOL;
- median net SOL: -1.9982 SOL;
- minimum: -2.7750 SOL;
- maximum: -0.9757 SOL;
- mean ROI: -14.30%; and
- median ROI: -14.64%.

Every sampled random seed is negative under the reconstructed reference
accounting and fee assumptions.

## 20. Paired comparisons

Paired round-bootstrap differences use mean net lamports per opportunity and
500 deterministic round resamples.

| Candidate | Baseline | Estimate | 95% interval |
|---|---|---:|---:|
| Random Forest all-72 | seeded random | +209,738 | [-87,569, +509,855] |
| Random Forest all-72 | least miner | +181,052 | [-405,005, +705,717] |
| Random Forest all-72 | least deployed | +465,202 | [-23,511, +895,686] |
| HistGradientBoosting all-72 | seeded random | +213,348 | [-100,303, +580,837] |
| HistGradientBoosting all-72 | least miner | +184,661 | [-337,874, +722,943] |
| HistGradientBoosting all-72 | least deployed | +468,812 | [+12,670, +997,634] |

Except for boosting versus least-deployed, intervals include zero. This is not
robust evidence of a general economic advantage.

## 21. SOL economics and fee impact

Full OOS reference results:

| Strategy | Net before fees | Fees | Net after fees | ROI after fees |
|---|---:|---:|---:|---:|
| HistGradientBoosting all-72 | +1.0431 SOL | 0.0717 SOL | +0.9714 SOL | +7.12% |
| Random Forest all-72 | +0.9181 SOL | 0.0717 SOL | +0.8464 SOL | +6.20% |
| Highest reward | — | — | +0.8988 SOL | +6.58% |
| Seeded random | -1.9303 SOL | 0.0710 SOL | -2.0013 SOL | -14.66% |
| Least miner | — | — | -1.5257 SOL | -11.18% |
| Least deployed | — | — | -5.4927 SOL | -40.23% |

For Random Forest, before-fee ROI is 6.72% at every size by construction of
the price-taking equation. After-fee ROI is:

- -3.78% at 0.00005 SOL;
- +1.47% at 0.00010 SOL;
- +4.62% at 0.00025 SOL;
- +5.67% at 0.00050 SOL; and
- +6.20% at 0.00100 SOL.

Fees erase the apparent edge at the smallest size. Larger-size improvement is
a fixed-fee artifact inside a linear reconstructed model, not verification
that real protocol ROI is size-invariant.

## 22. Square-count and allocation findings

At 0.001 SOL:

- Random Forest all-72 top-1 ROI is +6.20%.
- Top-2 is +5.04% equal and +5.42% rank decay.
- Top-3 is -1.25% equal and +1.91% rank decay.
- Top-5 rank decay is approximately break-even (+0.03%).
- HistGradientBoosting is positive only at top-1.

Rank decay helps Random Forest at top-2 through top-5 and reduces boosting
losses beyond top-1, but it is not uniformly superior across heuristics.
Selecting more squares raises winner coverage and can reduce drawdown, but
generally dilutes reconstructed return. Top-1 has the strongest aggregate
economic result for the positive tree configurations.

## 23. ORE production and concentration

Every deployable OOS strategy/scenario earns zero measurable ORE because:

- base ORE is unavailable; and
- no OOS round contains a Motherlode.

No ORE concentration, motherlode-exclusion, ORE-per-SOL, or break-even ORE
conclusion is possible. Excluding Motherlodes leaves SOL results unchanged.

## 24. Combined price sensitivity

Hypothetical SOL prices are $100 and $200. Hypothetical ORE prices are $1,
$5, and $10.

Because reconstructed OOS ORE is zero, changing ORE price has no effect. The
combined scenario reduces to net SOL multiplied by the assumed SOL price.
These values are not realized USD returns.

## 25. Bankroll and drawdown

Reference top-1, 0.001 SOL normalized paths:

- Every strategy eventually stops participating from 0.1, 0.5, and 1.0 SOL.
- At 5 SOL, boosting all-72/52 ends near 5.971 SOL, highest reward near
  5.899 SOL, and Random Forest all-72 near 5.846 SOL.
- At 5 SOL, Random Forest all-72 maximum drawdown is about 1.981 SOL versus
  2.694 SOL for boosting and 6.397 SOL for highest reward.

Among positive, fully participating reference strategies, Random Forest
all-72 has the best drawdown profile. These paths process independent
observation opportunities sequentially and must not be interpreted as a
deployable repeated-within-round bankroll forecast.

## 26. Leakage safeguards

Runtime checks enforce:

- canonical dataset hash;
- exact RFC-004 fold boundaries;
- disjoint OOS round blocks;
- exact 72-feature manifest;
- frozen 52-feature configuration;
- 13,652 OOS opportunities per strategy;
- valid top-1 selected squares;
- finite ranks and identifiers;
- outcome-source agreement;
- no missing finalized economics;
- no future/outcome fields in selection helpers; and
- tracked assumptions independent of price-scenario reporting.

Outcome fields are used only after the RFC-004 decision/rank summary is frozen.
The final holdout affects reporting only.

## 27. Reproducibility

Two independent canonical runs completed in 41.707 and 42.140 seconds.

The following outputs were byte-identical:

- strategy metrics;
- opportunity accounting;
- bankroll paths;
- bootstrap intervals;
- assumptions;
- strategy definitions.

The results JSON was substantively identical after excluding only
`runtime_seconds`. Integer accounting is exact; the accepted tolerance for
derived floating ratios is `1e-12`.

## 28. Limitations

Blocking evidence limitations:

- no historical participant wallet ledger;
- no observed fees or failed transactions;
- no verified participant payout equation;
- base ORE unavailable;
- zero OOS Motherlodes;
- only 22 directly observed OOS rounds;
- full model rank vectors absent, preventing canonical ensembles and exact
  top-k selected identities;
- repeated within-round observations are independent counterfactual
  opportunities, not a single executable path;
- outcome-source and temporal instability; and
- price-taking results do not model strategy impact on denominators.

## 29. Direct answers

1. **Model versus seeded random:** tree models are positive in aggregate while
   all 20 random seeds are negative, but paired intervals cross zero.
2. **Model versus least-miner:** aggregate tree results are better; paired
   intervals cross zero and holdout least-miner is stronger.
3. **Model versus least-deployed:** both all-72 trees are better in aggregate;
   only boosting's paired interval is narrowly above zero.
4. **Model versus least-crowded:** same conclusion as least-miner because the
   rankings coincide.
5. **Chronological consistency:** no. Random Forest is negative in three of
   four blocks; boosting is negative in validation_1.
6. **Observed versus enriched consistency:** no. Boosting reverses sign and
   sample power is limited.
7. **More than one square:** it increases coverage and sometimes lowers
   drawdown, but top-1 has the best aggregate return for positive models.
8. **Rank decay versus equal:** helpful for model top-k dilution, not
   universally superior.
9. **Deployment-size sensitivity:** fixed fees erase the edge at 0.00005 SOL;
   apparent ROI improves with size because the reconstructed payout is linear.
10. **ORE concentration:** unmeasurable; no OOS ORE is available.
11. **Without Motherlodes:** SOL results are unchanged because no OOS
    Motherlode exists.
12. **Transaction/claim costs:** they erase the smallest-size edge but not the
    aggregate reference-size tree result.
13. **Execution friction:** the reconstructed signal can exceed assumed fees
    at some sizes, but instability and missing realized mechanics prevent a
    credible survival claim.
14. **Best drawdown:** Random Forest all-72 among positive, fully participating
    reference strategies.
15. **Best ORE-per-SOL:** none; every OOS value is zero.
16. **Adaptive/probability sizing:** no. RFC-004 probabilities are not
    calibrated and RFC-005 uses ranking only.
17. **Evidence for live testing:** no. Twenty-two observed OOS rounds and no
    wallet-realized economics are insufficient.
18. **Next phase:** collect directly observed wallet, fee, return, claim, base
    ORE, and Motherlode data while continuing paper simulation. Do not begin
    controlled live deployment.

## 30. Decision and next gate

RFC-005 does not approve a live strategy.

The all-72 tree rankings remain research candidates for paper evaluation, with
Random Forest offering the better reconstructed drawdown profile and boosting
the larger aggregate reference return. Neither satisfies the decision rules:
fold consistency, robust paired advantage, verified execution friction,
directly observed economic evidence, and ORE accounting are missing.

The recommended next gate is an economic-data collection RFC that records
wallet-level deploys, transaction fees, failed attempts, returns, ORE claims,
claim timing/batching, and full per-square OOS model rankings. Re-run RFC-005
only after those fields are available.

## Commands and generated outputs

Canonical command:

```text
PYTHONPATH=src .venv/bin/python -m orev3.economics.cli \
  --seed 20260725
```

Validation-only:

```text
PYTHONPATH=src .venv/bin/python -m orev3.economics.cli \
  --validation-only --seed 20260725
```

Generated and ignored:

- `data/research/economic_simulation_results_v1.json`
- `data/research/economic_strategy_metrics_v1.csv`
- `data/research/economic_opportunity_results_v1.csv`
- `data/research/economic_bankroll_paths_v1.csv`
- `data/research/economic_assumptions_v1.json`
- `data/research/economic_strategy_definitions_v1.json`
- `data/research/economic_bootstrap_intervals_v1.csv`

Required verification:

```text
PYTHONPATH=src .venv/bin/pytest -q tests/economics
PYTHONPATH=src .venv/bin/pytest -q tests/modeling
PYTHONPATH=src .venv/bin/pytest -q tests/features
PYTHONPATH=src .venv/bin/pytest -q tests/datasets
PYTHONPATH=src .venv/bin/pytest -q tests
```
