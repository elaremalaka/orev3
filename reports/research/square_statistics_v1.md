# RFC-001: Square Statistics v1

## Status

Generated descriptive analysis. No strategy decision is authorized by this report alone.

## Dataset

- Path: `data/research/square_features_v1_slots_20.csv`
- SHA-256: `5c4cadae157684e5dae994b9e2c4032d7e980e77c87bd7c58e61c08d96167b6d`
- Rows: 10925
- Rounds: 437
- Columns: 41
- Schema versions: 1.0.0
- Feature versions: 1.0.0
- Dataset versions: square_features_v1
- Generated at: 2026-07-24T05:44:14.106354+00:00

## Scope

This analysis evaluates square location, geometry, miner congestion, neighbor congestion, missingness, and simple univariate correlations.

Per-square SOL features are not evaluated because the current replay dataset does not expose them.

## Observations

- Square 20 had the highest observed lift versus a uniform 4% square win rate (1.659x).
- Square 6 had the lowest observed lift versus uniform (0.515x).
- The strongest geometry group by observed win-share lift was corner (1.259x).
- These are descriptive observations only. They are not evidence of a deployable edge without chronological validation.

## Top squares by observed lift

| square_index | wins | win_rate | win_rate_lift_vs_uniform | mean_miners | mean_miner_share | mean_neighbor_miners |
| --- | --- | --- | --- | --- | --- | --- |
| 20 | 29 | 0.066362 | 1.659039 | 139.668192 | 0.040332 | 136.718535 |
| 4 | 25 | 0.057208 | 1.430206 | 139.208238 | 0.040233 | 137.193364 |
| 8 | 24 | 0.054920 | 1.372998 | 140.796339 | 0.040684 | 135.583524 |
| 1 | 22 | 0.050343 | 1.258581 | 134.480549 | 0.038869 | 140.627002 |
| 17 | 22 | 0.050343 | 1.258581 | 137.970252 | 0.039849 | 140.212243 |
| 0 | 21 | 0.048055 | 1.201373 | 138.711670 | 0.040066 | 136.712815 |
| 12 | 21 | 0.048055 | 1.201373 | 141.709382 | 0.040953 | 137.068650 |
| 2 | 20 | 0.045767 | 1.144165 | 144.052632 | 0.041610 | 136.130435 |
| 10 | 20 | 0.045767 | 1.144165 | 142.022883 | 0.041057 | 139.963387 |
| 19 | 20 | 0.045767 | 1.144165 | 134.716247 | 0.038910 | 138.827613 |

## Geometry statistics

| geometry | unique_squares | wins | observed_win_share | uniform_win_share | win_share_lift_vs_uniform | mean_miners |
| --- | --- | --- | --- | --- | --- | --- |
| corner | 4 | 88 | 0.201373 | 0.160000 | 1.258581 | 139.879291 |
| edge | 12 | 197 | 0.450801 | 0.480000 | 0.939169 | 137.949275 |
| interior | 8 | 131 | 0.299771 | 0.320000 | 0.936785 | 138.096968 |
| center | 1 | 21 | 0.048055 | 0.040000 | 1.201373 | 141.709382 |

## Correlations with winning label

Pearson correlations are descriptive and can be distorted by repeated within-round structure. They are included for screening only.

| feature | correlation_with_won | absolute_correlation | non_null_rows |
| --- | --- | --- | --- |
| orthogonal_neighbor_count | -0.015776 | 0.015776 | 10925 |
| miner_rank_descending | -0.014251 | 0.014251 | 10925 |
| miner_rank_ascending | 0.014186 | 0.014186 | 10925 |
| orthogonal_neighbor_miners | -0.013565 | 0.013565 | 10925 |
| miner_share | 0.010973 | 0.010973 | 10925 |
| board_column | -0.008918 | 0.008918 | 10925 |
| square_index | -0.008226 | 0.008226 | 10925 |
| board_row | -0.006606 | 0.006606 | 10925 |
| distance_from_center | 0.006575 | 0.006575 | 10925 |
| is_bottom4_miners | -0.006269 | 0.006269 | 10925 |
| miner_count | 0.004311 | 0.004311 | 10925 |
| is_top4_miners | 0.002650 | 0.002650 | 10925 |
| orthogonal_neighbor_mean_miners | -0.001482 | 0.001482 | 10925 |
| total_board_miners | 0.000000 | 0.000000 | 10925 |
| exact_slot_match | -0.000000 | 0.000000 | 10925 |

## Missingness

| column | missing_rows | total_rows | missing_rate |
| --- | --- | --- | --- |
| average_sol_per_miner_raw | 10925 | 10925 | 1.000000 |
| orthogonal_neighbor_mean_sol_raw | 10925 | 10925 | 1.000000 |
| orthogonal_neighbor_sol_raw | 10925 | 10925 | 1.000000 |
| sol_share | 10925 | 10925 | 1.000000 |
| square_sol_raw | 10925 | 10925 | 1.000000 |
| total_board_sol_raw | 10925 | 10925 | 1.000000 |

## Interpretation constraints

- The 25 rows within a round are not independent observations.
- Square-level differences may be noise in this sample.
- No chronological holdout was used.
- No transaction costs or payout economics were evaluated.
- No strategy should be promoted from this report alone.

## Recommended next decision

Use this report to select narrowly scoped hypotheses for chronological testing. Do not convert the largest descriptive difference directly into a live strategy.
