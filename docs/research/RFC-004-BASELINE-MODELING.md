# RFC-004 — Baseline Modeling and Grouped Chronological Evaluation

## Status and scope

RFC-004 is an experimental ranking baseline. It does not select a production
strategy, estimate profitability, size deployments, integrate with live mining,
or tune hyperparameters.

The experiment asks whether the RFC-003B square-feature dataset contains
chronologically out-of-sample ranking signal beyond simple current-observation
heuristics.

## Canonical input and target

The runner validates the canonical artifacts before fitting:

- `data/research/square_feature_dataset_v1.csv`
- `data/research/square_feature_dataset_v1.manifest.json`
- dataset SHA-256:
  `9047141c99e2eb067bc0ca0bc5ee082ed141f91f16e25c23e125b062bf97983d`
- 72 manifest-declared predictive columns
- 439 rounds
- 33,956 observations
- 848,900 rows
- exactly 25 rows per observation
- no duplicate square keys
- no missing or non-finite predictive values

`won` is the supervised row label. An observation is usable only when it has
25 square rows, exactly one `won=1`, a non-empty `outcome_source`, and
`winning_square` agrees with the positive row. All canonical observations pass.
There are 381 enriched rounds and 58 observed rounds. Source is retained for
reporting but never used as a predictor.

## Leakage controls

The manifest feature list is the only source of predictive columns. Round,
observation, and square identifiers; progress metadata; labels; outcome source;
coverage status; and final or future fields are excluded.

Rounds are sorted by ascending numeric `round_id`, the repository's available
chronology field. Each fold contains complete round groups. Training always
precedes evaluation, and preprocessing is fitted on training rows only.

The conservative feature list is selected once using only the first 263
training rounds, following the RFC-003B.3 policy for constants, exact
duplicates, identical availability flags, and perfectly affine columns. It is
then frozen for every validation fold and the holdout. Evaluation rows do not
influence scaling, fitting, feature selection, sample weights, congestion
thresholds, calibration fitting, or model settings.

## Chronological design

The 439 rounds divide exactly into one initial window and four 44-round forward
blocks.

| Fold | Kind | Training rounds | Training observations | Evaluation rounds | Evaluation observations |
|---|---|---:|---:|---:|---:|
| validation_1 | validation | 342132–342394 (263) | 20,304 | 342395–342438 (44) | 3,399 |
| validation_2 | validation | 342132–342438 (307) | 23,703 | 342439–342482 (44) | 3,413 |
| validation_3 | validation | 342132–342482 (351) | 27,116 | 342483–342526 (44) | 3,424 |
| final_holdout | holdout | 342132–342526 (395) | 30,540 | 342527–342570 (44) | 3,416 |

The holdout is reported once and was not used to change features,
hyperparameters, thresholds, or model selection.

## Feature configurations and weighting

`all_72` contains every manifest feature. `conservative_deduplicated` contains
52 features and excludes 20 initial-training constants or exact/perfect-affine
aliases. The exact ordered lists and exclusion reasons are recorded in
`baseline_feature_sets_v1.json`. High-correlation and near-constant features
are not removed.

Every observation has total training weight 1:

- winner weight: `0.5`
- each of 24 loser weights: `0.5 / 24`

This balances positive and negative class mass while giving every observation
equal total weight. Rounds with more observations intentionally contribute
more observed board states; results are still reported by round and uncertainty
is resampled by round.

## Fixed models and baselines

The environment uses scikit-learn 1.9.0.

- Logistic Regression: train-only `StandardScaler`, `C=1`, `lbfgs`,
  `max_iter=100`.
- Random Forest: 40 trees, maximum depth 10, minimum leaf size 20,
  square-root feature sampling.
- HistGradientBoosting: learning rate 0.05, 50 iterations, 31 leaves,
  minimum leaf size 50, L2 regularization 1.

All stochastic components use seed `20260725`. No search was run.

Non-ML rankings are seeded random, uniform, least miner count, least deployed
lamports, lowest miner share, highest reward, and the existing least-crowded
heuristic. Ties use ascending `square_index`. Lowest miner share and the
existing least-crowded heuristic reproduce least miner count on this dataset.
Highest reward reproduces uniform ranking because its evaluated scores tie.

Model positive-class probabilities are normalized to sum to one within each
25-square observation. Uniform is the only heuristic assigned probabilities.

## Metrics

Primary metrics are calculated once per observation: top-1/2/3/5, reciprocal
rank, mean and median winner rank, single-relevant-item NDCG, and winner
percentile. Probability diagnostics are multiclass log loss, summed multiclass
Brier score, mean winner probability, and equal-frequency calibration bins.

Metrics are saved per fold and by outcome source, progress bucket,
training-derived congestion bucket, and coverage where present. Round-level
bootstrap intervals use 500 deterministic resamples. Strategy-relative output
records agreement, incremental hits, lost hits, and winner-rank improvement,
including progress, congestion, and coverage segments.

## Results

### Validation means across three folds

| Configuration / strategy | Top-1 | Fold SD | MRR | Mean winner rank | Log loss |
|---|---:|---:|---:|---:|---:|
| Seeded random | 0.0397 | 0.0032 | 0.1532 | 12.94 | — |
| Least miner | 0.0309 | 0.0145 | 0.1360 | 13.60 | — |
| Least deployed | 0.0309 | 0.0131 | 0.1448 | 13.24 | — |
| Uniform | 0.0377 | 0.0382 | 0.1482 | 13.21 | 3.2189 |
| Logistic, all 72 | 0.0254 | 0.0096 | 0.1438 | 12.57 | 3.2195 |
| Random Forest, all 72 | **0.0521** | 0.0128 | **0.1678** | **12.46** | 3.2376 |
| HistGradientBoosting, all 72 | 0.0510 | 0.0149 | 0.1638 | 12.65 | 3.2379 |
| Logistic, deduplicated | 0.0254 | 0.0096 | 0.1441 | 12.57 | 3.2196 |
| Random Forest, deduplicated | 0.0443 | 0.0160 | 0.1582 | 12.46 | 3.2363 |
| HistGradientBoosting, deduplicated | 0.0510 | 0.0149 | 0.1638 | 12.65 | 3.2379 |

The all-72 Random Forest top-1 values by fold were 0.0447, 0.0416, and
0.0701, compared with random at 0.0382, 0.0366, and 0.0441. Its MRR exceeded
random, least miner, and least deployed in all three validation folds.

### Final holdout

| Configuration / strategy | Top-1 | MRR | Mean winner rank | Log loss |
|---|---:|---:|---:|---:|
| Seeded random | 0.0413 | 0.1539 | 12.96 | — |
| Least miner | **0.0723** | 0.1616 | 14.03 | — |
| Least deployed | 0.0167 | 0.1309 | 12.58 | — |
| Uniform | **0.0907** | **0.1979** | 12.75 | 3.2189 |
| Logistic, all 72 | 0.0495 | 0.1503 | 13.47 | 3.2227 |
| Random Forest, all 72 | 0.0442 | 0.1685 | **12.64** | 3.2288 |
| HistGradientBoosting, all 72 | 0.0474 | 0.1571 | 12.98 | 3.2263 |
| Logistic, deduplicated | 0.0498 | 0.1507 | 13.49 | 3.2227 |
| Random Forest, deduplicated | 0.0196 | 0.1426 | 12.78 | 3.2420 |
| HistGradientBoosting, deduplicated | 0.0474 | 0.1571 | 12.98 | 3.2263 |

Uniform and highest reward are deterministic square-index tie rankings here,
not random controls. Their holdout result reflects a late concentration of
winners at the lowest tie-break index and is evidence of temporal instability,
not a useful reward-based signal.

Across all 176 out-of-sample rounds, the all-72 Random Forest round-bootstrap
95% intervals are `[0.0367, 0.0656]` for top-1 and `[0.1492, 0.1864]` for
MRR. Random intervals are `[0.0369, 0.0435]` and `[0.1501, 0.1566]`.
The overlap and fold dispersion require conservative interpretation.

Tree top-1 performance fell from validation_3 to holdout: Random Forest from
0.0701 to 0.0442 and HistGradientBoosting from 0.0689 to 0.0474. Logistic
Regression moved in the opposite direction, so deterioration is not monotonic
across model families.

## Source, calibration, and feature diagnostics

Observed outcomes are a small, chronologically clustered subset: each
validation block has only five observed rounds, and the holdout has seven.
Performance differs materially by source and fold. For example, validation_2
all-72 Random Forest top-1 is 0.1662 on observed versus 0.0258 on enriched,
whereas validation_3 is 0.0000 versus 0.0792. This prevents a source-invariant
conclusion. Source-specific calibration ECE is also worse on observed data
(roughly 0.019 for tree models) than enriched data (roughly 0.007–0.008).

Overall validation calibration ECE ranges from approximately 0.0027 to 0.0102,
but this should not be mistaken for useful probabilistic skill. Mean winner
probabilities remain near the 0.04 base rate, and every model's mean validation
and holdout log loss is no better than uniform. The models have limited ranking
resolution and weak probability calibration.

Native importance is redundant-feature-sensitive and not causal. Across the
three validation folds, relative features account for about 62%–64% of summed
Logistic/Random-Forest native magnitude, temporal features about 30%–36%, and
raw features about 1%–7%. Stable high-magnitude logistic terms include
`miner_z_score`, `miner_difference_from_mean`, `deployed_z_score`,
`deployed_outflow_rate_1`, leader-history features,
`board_total_miner_delta_1`, and `deployed_rolling_std_3`. Random Forest
importance repeatedly emphasizes deployed relative features, miner relative
features, deployed lamports, and deployed rolling means. HistGradientBoosting
does not expose native feature importance in scikit-learn; full-dataset SHAP
and expensive permutation analysis were intentionally omitted.

Only two partial-start rounds exist, both inside the initial training window.
There is therefore no out-of-sample complete-versus-partial comparison.
Progress and congestion diagnostics are saved, but their instability across
folds does not support a durable segment claim.

## Reproducibility

Two independent full runs used identical inputs, folds, feature sets, and
seeds. Feature lists, native importance values, selected squares, and winner
ranks matched exactly. Parallel Random Forest winner probabilities differed by
at most `1.11e-16`; the largest downstream metric difference was
`1.34e-15` in log loss. Wall-clock and per-fit timing fields are excluded from
substantive comparison. The accepted deterministic tolerance is `1e-12` for
floating-point probability and metric fields.

The canonical reporting run completed in 235.863 seconds. macOS physical-core
detection emitted a joblib warning and fell back to logical cores; execution
completed normally.

## Required conclusions

1. **Models versus random:** the all-72 Random Forest beats seeded random on
   top-1 in every forward block and on MRR in all blocks. HistGradientBoosting
   beats random in three of four blocks. The lift is modest and uncertainty
   overlaps.
2. **Models versus least-crowded/deployed:** Random Forest MRR is better in
   every block, but top-1 is not. Least miner wins holdout top-1. There is no
   robust top-1 superiority over the heuristics.
3. **Consistency:** Random Forest's random-relative direction is consistent,
   but magnitude, heuristic-relative results, and source segments are not.
4. **Later rounds:** tree performance drops sharply from validation_3 to the
   holdout, while Logistic Regression improves. Drift is present but not a
   simple monotonic decline.
5. **All 72 versus deduplicated:** neither dominates universally.
   HistGradientBoosting rankings are identical and Logistic Regression is
   effectively unchanged. Random Forest favors all 72, especially on holdout.
6. **Useful feature families:** relative features are most consistently
   prominent; temporal features contribute a meaningful secondary share.
   Importance is diluted by redundancy and is not causal.
7. **Calibration:** probabilities are near the base rate and do not beat
   uniform log loss. Calibration is insufficient for economic sizing.
8. **Economic simulation:** the ranking signal is large enough to justify a
   tightly controlled, leakage-safe economic simulation as the next research
   gate, but not production strategy selection or live deployment.
9. **Outcome sources:** observed and enriched results differ materially and
   sometimes reverse by fold. They must remain separate in later work.
10. **Largest RFC-005 risks:** temporal drift, source/regime confounding, only
    58 observed rounds, deterministic tie/index effects, absent out-of-sample
    partial coverage, weak probability skill, redundant-feature importance,
    and lack of a validated leakage-safe economic outcome model.

## Outputs and commands

Generated outputs remain ignored under repository policy:

- `data/research/baseline_model_results_v1.json`
- `data/research/baseline_fold_metrics_v1.csv`
- `data/research/baseline_predictions_v1.csv`
- `data/research/baseline_feature_sets_v1.json`
- `data/research/baseline_feature_importance_v1.csv`

Run the experiment:

```text
PYTHONPATH=src .venv/bin/python -m orev3.modeling.run_baseline_modeling
```

Run verification:

```text
PYTHONPATH=src .venv/bin/pytest -q tests/modeling
PYTHONPATH=src .venv/bin/pytest -q tests/features
PYTHONPATH=src .venv/bin/pytest -q tests/datasets
PYTHONPATH=src .venv/bin/pytest -q tests
```
