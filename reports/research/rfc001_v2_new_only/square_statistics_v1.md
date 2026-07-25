# RFC-001: Square Statistics v1

## Status

Generated descriptive analysis. No strategy decision is authorized by this report alone.

## Dataset

- Path: `data/research/square_features_v2_new_only_slots_20.csv`
- SHA-256: `6a90e561cfef49663c8482faa5aa2cee884b5a70fc6f8d89c24f0c87a8386f47`
- Rows: 21100
- Rounds: 844
- Columns: 41
- Schema versions: 1.0.0
- Feature versions: 1.0.0
- Dataset versions: square_features_v1
- Generated at: 2026-07-25T01:13:29.903345+00:00

## Scope

This analysis evaluates square location, geometry, miner congestion, neighbor congestion, missingness, and simple univariate correlations.

Per-square SOL features are not evaluated because the current replay dataset does not expose them.

## Observations

- Square 19 had the highest observed lift versus a uniform 4% square win rate (1.422x).
- Square 23 had the lowest observed lift versus uniform (0.770x).
- The strongest geometry group by observed win-share lift was edge (1.044x).
- These are descriptive observations only. They are not evidence of a deployable edge without chronological validation.

## Top squares by observed lift

| square_index | wins | win_rate | win_rate_lift_vs_uniform | mean_miners | mean_miner_share | mean_neighbor_miners |
| --- | --- | --- | --- | --- | --- | --- |
| 19 | 48 | 0.056872 | 1.421801 | 137.563981 | 0.039193 | 140.909558 |
| 3 | 43 | 0.050948 | 1.273697 | 141.258294 | 0.040249 | 141.851896 |
| 10 | 43 | 0.050948 | 1.273697 | 143.783175 | 0.040977 | 141.673381 |
| 17 | 42 | 0.049763 | 1.244076 | 142.849526 | 0.040704 | 142.129443 |
| 1 | 38 | 0.045024 | 1.125592 | 137.526066 | 0.039191 | 141.050158 |
| 5 | 38 | 0.045024 | 1.125592 | 139.518957 | 0.039756 | 141.162717 |
| 8 | 36 | 0.042654 | 1.066351 | 143.225118 | 0.040812 | 138.499704 |
| 20 | 36 | 0.042654 | 1.066351 | 140.111374 | 0.039924 | 139.843602 |
| 9 | 35 | 0.041469 | 1.036730 | 137.303318 | 0.039120 | 140.375987 |
| 11 | 33 | 0.039100 | 0.977488 | 143.644550 | 0.040933 | 142.041765 |

## Geometry statistics

| geometry | unique_squares | wins | observed_win_share | uniform_win_share | win_share_lift_vs_uniform | mean_miners |
| --- | --- | --- | --- | --- | --- | --- |
| corner | 4 | 127 | 0.150474 | 0.160000 | 0.940462 | 140.516884 |
| edge | 12 | 423 | 0.501185 | 0.480000 | 1.044135 | 139.669530 |
| interior | 8 | 265 | 0.313981 | 0.320000 | 0.981191 | 140.876629 |
| center | 1 | 29 | 0.034360 | 0.040000 | 0.859005 | 144.202607 |

## Correlations with winning label

Pearson correlations are descriptive and can be distorted by repeated within-round structure. They are included for screening only.

| feature | correlation_with_won | absolute_correlation | non_null_rows |
| --- | --- | --- | --- |
| miner_rank_ascending | -0.005366 | 0.005366 | 21100 |
| miner_share | -0.005366 | 0.005366 | 21100 |
| miner_rank_descending | 0.004226 | 0.004226 | 21100 |
| is_top4_miners | -0.003985 | 0.003985 | 21100 |
| orthogonal_neighbor_mean_miners | 0.003512 | 0.003512 | 21100 |
| distance_from_center | 0.003208 | 0.003208 | 21100 |
| miner_count | -0.002546 | 0.002546 | 21100 |
| board_row | -0.002223 | 0.002223 | 21100 |
| board_column | 0.002052 | 0.002052 | 21100 |
| square_index | -0.001778 | 0.001778 | 21100 |
| is_bottom4_miners | -0.000686 | 0.000686 | 21100 |
| orthogonal_neighbor_count | -0.000628 | 0.000628 | 21100 |
| orthogonal_neighbor_miners | 0.000045 | 0.000045 | 21100 |
| total_board_miners | -0.000000 | 0.000000 | 21100 |
| replay_slot_distance | -0.000000 | 0.000000 | 21100 |

## Missingness

| column | missing_rows | total_rows | missing_rate |
| --- | --- | --- | --- |
| average_sol_per_miner_raw | 21100 | 21100 | 1.000000 |
| orthogonal_neighbor_mean_sol_raw | 21100 | 21100 | 1.000000 |
| orthogonal_neighbor_sol_raw | 21100 | 21100 | 1.000000 |
| sol_share | 21100 | 21100 | 1.000000 |
| square_sol_raw | 21100 | 21100 | 1.000000 |
| total_board_sol_raw | 21100 | 21100 | 1.000000 |

## Interpretation constraints

- The 25 rows within a round are not independent observations.
- Square-level differences may be noise in this sample.
- No chronological holdout was used.
- No transaction costs or payout economics were evaluated.
- No strategy should be promoted from this report alone.

## Recommended next decision

Use this report to select narrowly scoped hypotheses for chronological testing. Do not convert the largest descriptive difference directly into a live strategy.
