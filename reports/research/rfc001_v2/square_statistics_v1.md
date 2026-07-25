# RFC-001: Square Statistics v1

## Status

Generated descriptive analysis. No strategy decision is authorized by this report alone.

## Dataset

- Path: `data/research/square_features_v2_slots_20.csv`
- SHA-256: `504801ab9cb9948de2cd13622aa9454ff841488d4d13ecb36a9321ed5cc8bbee`
- Rows: 22525
- Rounds: 901
- Columns: 41
- Schema versions: 1.0.0
- Feature versions: 1.0.0
- Dataset versions: square_features_v1
- Generated at: 2026-07-25T01:04:42.493709+00:00

## Scope

This analysis evaluates square location, geometry, miner congestion, neighbor congestion, missingness, and simple univariate correlations.

Per-square SOL features are not evaluated because the current replay dataset does not expose them.

## Observations

- Square 19 had the highest observed lift versus a uniform 4% square win rate (1.415x).
- Square 23 had the lowest observed lift versus uniform (0.721x).
- The strongest geometry group by observed win-share lift was edge (1.031x).
- These are descriptive observations only. They are not evidence of a deployable edge without chronological validation.

## Top squares by observed lift

| square_index | wins | win_rate | win_rate_lift_vs_uniform | mean_miners | mean_miner_share | mean_neighbor_miners |
| --- | --- | --- | --- | --- | --- | --- |
| 19 | 51 | 0.056604 | 1.415094 | 137.294118 | 0.039169 | 140.703293 |
| 3 | 45 | 0.049945 | 1.248613 | 141.002220 | 0.040230 | 141.753607 |
| 10 | 44 | 0.048835 | 1.220866 | 143.612653 | 0.040986 | 141.497595 |
| 17 | 44 | 0.048835 | 1.220866 | 142.457270 | 0.040645 | 141.940622 |
| 1 | 41 | 0.045505 | 1.137625 | 137.281909 | 0.039175 | 140.960784 |
| 5 | 41 | 0.045505 | 1.137625 | 139.419534 | 0.039782 | 141.026637 |
| 8 | 39 | 0.043285 | 1.082131 | 143.003330 | 0.040805 | 138.237236 |
| 20 | 37 | 0.041065 | 1.026637 | 140.016648 | 0.039950 | 139.577691 |
| 9 | 36 | 0.039956 | 0.998890 | 137.152053 | 0.039132 | 140.225305 |
| 18 | 36 | 0.039956 | 0.998890 | 141.319645 | 0.040321 | 138.026637 |

## Geometry statistics

| geometry | unique_squares | wins | observed_win_share | uniform_win_share | win_share_lift_vs_uniform | mean_miners |
| --- | --- | --- | --- | --- | --- | --- |
| corner | 4 | 136 | 0.150943 | 0.160000 | 0.943396 | 140.412042 |
| edge | 12 | 446 | 0.495006 | 0.480000 | 1.031262 | 139.492323 |
| interior | 8 | 284 | 0.315205 | 0.320000 | 0.985017 | 140.625832 |
| center | 1 | 35 | 0.038846 | 0.040000 | 0.971143 | 143.984462 |

## Correlations with winning label

Pearson correlations are descriptive and can be distorted by repeated within-round structure. They are included for screening only.

| feature | correlation_with_won | absolute_correlation | non_null_rows |
| --- | --- | --- | --- |
| miner_rank_ascending | -0.003707 | 0.003707 | 22525 |
| miner_share | -0.003384 | 0.003384 | 22525 |
| miner_rank_descending | 0.003110 | 0.003110 | 22525 |
| orthogonal_neighbor_mean_miners | 0.002981 | 0.002981 | 22525 |
| is_bottom4_miners | -0.002571 | 0.002571 | 22525 |
| is_top4_miners | -0.002571 | 0.002571 | 22525 |
| board_row | -0.002243 | 0.002243 | 22525 |
| board_column | 0.002243 | 0.002243 | 22525 |
| square_index | -0.001759 | 0.001759 | 22525 |
| orthogonal_neighbor_miners | 0.001530 | 0.001530 | 22525 |
| miner_count | -0.001299 | 0.001299 | 22525 |
| orthogonal_neighbor_count | 0.000916 | 0.000916 | 22525 |
| distance_from_center | 0.000468 | 0.000468 | 22525 |
| actual_slots_remaining | -0.000000 | 0.000000 | 22525 |
| replay_slot_distance | -0.000000 | 0.000000 | 22525 |

## Missingness

| column | missing_rows | total_rows | missing_rate |
| --- | --- | --- | --- |
| average_sol_per_miner_raw | 22525 | 22525 | 1.000000 |
| orthogonal_neighbor_mean_sol_raw | 22525 | 22525 | 1.000000 |
| orthogonal_neighbor_sol_raw | 22525 | 22525 | 1.000000 |
| sol_share | 22525 | 22525 | 1.000000 |
| square_sol_raw | 22525 | 22525 | 1.000000 |
| total_board_sol_raw | 22525 | 22525 | 1.000000 |

## Interpretation constraints

- The 25 rows within a round are not independent observations.
- Square-level differences may be noise in this sample.
- No chronological holdout was used.
- No transaction costs or payout economics were evaluated.
- No strategy should be promoted from this report alone.

## Recommended next decision

Use this report to select narrowly scoped hypotheses for chronological testing. Do not convert the largest descriptive difference directly into a live strategy.
