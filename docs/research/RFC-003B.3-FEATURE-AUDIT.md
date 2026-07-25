# RFC-003B.3 — Feature Quality Audit

This report is diagnostic only. It does not train a model, select features, or estimate out-of-sample predictive power.

## Dataset integrity

- Audit passed: **True**
- Rounds: **439**
- Observations: **33,956**
- Square rows: **848,900**
- Predictive features: **72**
- Invalid observation shapes: **0**

## Thresholds and weighting

- Near-constant: one value occupies at least **99.5%** of finite rows.
- High correlation: absolute Pearson correlation at least **0.98**.
- Observation-balanced statistics give each observation total weight 1, divided equally across its finite square rows.
- Progress buckets: early [0,.2), early-middle [.2,.4), middle [.4,.6), late-middle [.6,.8), late [.8,1].

## Degenerate and near-constant features

- Constant: `has_reward_ever_led`
- Near-constant: `reward_raw`, `reward_delta_1`, `reward_delta_2`, `reward_delta_3`, `reward_rolling_mean_2`, `reward_rolling_mean_3`, `reward_ema_0_5`, `reward_momentum_3`, `reward_acceleration_1`, `miner_outflow_rate_1`, `deployed_outflow_rate_1`, `reward_rolling_std_3`, `reward_momentum_1`

## Temporal coverage

- History-dependent zero fallbacks lacking a mapped flag: **0**
- `deployed_observations_since_became_leader`: 34.01% available; first available observation index 0.
- `has_deployed_ever_led`: 34.01% available; first available observation index 0.
- `has_miner_ever_led`: 36.16% available; first available observation index 0.
- `miner_observations_since_became_leader`: 36.16% available; first available observation index 0.
- `deployed_delta_3`: 96.12% available; first available observation index 3.
- `has_history_3`: 96.12% available; first available observation index 3.
- `miner_delta_3`: 96.12% available; first available observation index 3.
- `reward_delta_3`: 96.12% available; first available observation index 3.
- `deployed_acceleration_1`: 97.41% available; first available observation index 2.
- `deployed_delta_2`: 97.41% available; first available observation index 2.

## Redundancy

- Threshold-passing relationships: **86**
- **high** `has_history_2` / `has_momentum_1`: availability_flags_identical (strength 1; 848,900 rows)
- **high** `has_history_2` / `has_rolling_window_3`: availability_flags_identical (strength 1; 848,900 rows)
- **high** `has_previous_observation` / `has_previous_board_observation`: availability_flags_identical (strength 1; 848,900 rows)
- **high** `has_rolling_window_3` / `has_momentum_1`: availability_flags_identical (strength 1; 848,900 rows)
- **high** `deployed_acceleration_1` / `deployed_momentum_1`: exact_duplicate (strength 1; 848,900 rows)
- **high** `deployed_leader_persistence` / `deployed_consecutive_leader_observations`: exact_duplicate (strength 1; 848,900 rows)
- **high** `miner_acceleration_1` / `miner_momentum_1`: exact_duplicate (strength 1; 848,900 rows)
- **high** `miner_leader_persistence` / `miner_consecutive_leader_observations`: exact_duplicate (strength 1; 848,900 rows)
- **high** `reward_acceleration_1` / `reward_momentum_1`: exact_duplicate (strength 1; 848,900 rows)
- **high** `reward_delta_1` / `reward_acceleration_1`: exact_duplicate (strength 1; 848,900 rows)
- **high** `reward_delta_1` / `reward_delta_2`: exact_duplicate (strength 1; 848,900 rows)
- **high** `reward_delta_1` / `reward_delta_3`: exact_duplicate (strength 1; 848,900 rows)
- **high** `reward_delta_1` / `reward_momentum_1`: exact_duplicate (strength 1; 848,900 rows)
- **high** `reward_delta_2` / `reward_acceleration_1`: exact_duplicate (strength 1; 848,900 rows)
- **high** `reward_delta_2` / `reward_delta_3`: exact_duplicate (strength 1; 848,900 rows)
- **high** `reward_delta_2` / `reward_momentum_1`: exact_duplicate (strength 1; 848,900 rows)
- **high** `reward_delta_3` / `reward_acceleration_1`: exact_duplicate (strength 1; 848,900 rows)
- **high** `reward_delta_3` / `reward_momentum_1`: exact_duplicate (strength 1; 848,900 rows)
- **high** `reward_raw` / `reward_acceleration_1`: exact_duplicate (strength 1; 848,900 rows)
- **high** `reward_raw` / `reward_delta_1`: exact_duplicate (strength 1; 848,900 rows)
- **high** `reward_raw` / `reward_delta_2`: exact_duplicate (strength 1; 848,900 rows)
- **high** `reward_raw` / `reward_delta_3`: exact_duplicate (strength 1; 848,900 rows)
- **high** `reward_raw` / `reward_momentum_1`: exact_duplicate (strength 1; 848,900 rows)
- **high** `reward_rolling_mean_2` / `reward_ema_0_5`: exact_duplicate (strength 1; 848,900 rows)
- **high** `reward_rolling_mean_3` / `reward_momentum_3`: exact_duplicate (strength 1; 848,900 rows)
- **high** `deployed_share` / `deployed_ratio_to_mean`: perfect_positive_affine (strength 1; 848,900 rows)
- **high** `miner_share` / `miner_ratio_to_mean`: perfect_positive_affine (strength 1; 848,900 rows)
- **high** `reward_acceleration_1` / `reward_rolling_std_3`: perfect_positive_affine (strength 1; 848,900 rows)
- **high** `reward_delta_1` / `reward_ema_0_5`: perfect_positive_affine (strength 1; 848,900 rows)
- **high** `reward_delta_1` / `reward_momentum_3`: perfect_positive_affine (strength 1; 848,900 rows)

## Strongest full-dataset label diagnostics

Observed and enriched outcomes are reported separately. These full-dataset differences are exploratory and must not be used as evidence of out-of-sample predictive power.

- `observed` / `deployed_difference_from_mean`: standardized difference -0.1369, mean difference -3.134e+06
- `observed` / `miner_difference_from_mean`: standardized difference 0.1223, mean difference 0.4185
- `observed` / `deployed_share`: standardized difference -0.1103, mean difference -0.0004036
- `observed` / `deployed_ratio_to_mean`: standardized difference -0.1103, mean difference -0.01009
- `observed` / `miner_z_score`: standardized difference 0.1071, mean difference 0.1027
- `observed` / `miner_average_rank`: standardized difference -0.08411, mean difference -0.5832
- `observed` / `deployed_z_score`: standardized difference -0.07816, mean difference -0.07376
- `enriched` / `deployed_z_score`: standardized difference 0.07202, mean difference 0.07243
- `observed` / `deployed_ratio_to_leader`: standardized difference -0.06923, mean difference -0.007504
- `enriched` / `miner_average_rank`: standardized difference -0.06615, mean difference -0.4718

## Leakage review

- Forbidden predictive columns: None
- Suspicious feature names: None
- Exact lag lookup and prefix-only history require continued manual review.

## Build performance

- Total build seconds: **170.89013304095715**
- Throughput: **198.70** observations/s; **4967.52** square rows/s.
- Sample: **1,068** observations / **26,700** square rows.
- Family `raw`: 0.0092 sampled compute seconds.
- Family `relative`: 0.6084 sampled compute seconds.
- Family `temporal`: 3.1207 sampled compute seconds.
- Class `rolling_dynamics`: 1.5377 seconds across 26,700 sampled calls.
- Class `temporal_expansion`: 1.1270 seconds across 26,700 sampled calls.
- Class `board_relative`: 0.6084 seconds across 26,700 sampled calls.
- Class `leader_dynamics`: 0.2175 seconds across 26,700 sampled calls.
- Class `lag_delta`: 0.1102 seconds across 26,700 sampled calls.
- Class `board_volatility`: 0.1011 seconds across 26,700 sampled calls.
- Class `one_step_delta`: 0.0274 seconds across 26,700 sampled calls.
- Class `raw_square`: 0.0092 seconds across 26,700 sampled calls.
- Retained all-history EMA lives in `rolling_dynamics`; its work grows with available square history and remains a manual performance-review priority.

## Recommended manual review priorities

1. Constant and near-constant features.
2. Exact duplicates, affine equivalents, and identical availability flags.
3. Legacy temporal zero fallbacks and all-history EMA cost.
4. Full-dataset winner/loser differences only after grouped chronological evaluation is designed.
5. Prefix-history and exact-lag leakage assumptions in the named source files.
