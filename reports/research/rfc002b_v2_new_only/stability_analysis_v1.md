# RFC-002B: Stability and Attribution

## Status

Chronological validation analysis. No live strategy authorization.

## Dataset

- Path: `data/research/square_features_v2_new_only_slots_20.csv`
- SHA-256: `6a90e561cfef49663c8482faa5aa2cee884b5a70fc6f8d89c24f0c87a8386f47`
- Rows: 21100
- Rounds: 844
- Chronology column: `start_slot`

## Split design

- Development: first 50% of rounds
- Validation: next 25% of rounds
- Confirmation: final 25% of rounds

## Candidate stability by split

| candidate | split | exclusion | observations | wins | rounds | win_rate | lift_vs_uniform |
| --- | --- | --- | --- | --- | --- | --- | --- |
| q4 | development | none | 2136 | 82 | 421 | 0.038390 | 0.959738 |
| corner_q3_q4 | development | none | 1094 | 37 | 417 | 0.033821 | 0.845521 |
| corner_rank13_21 | development | none | 922 | 30 | 409 | 0.032538 | 0.813449 |
| avoid_neighbor_q5 | development | none | 8362 | 325 | 422 | 0.038866 | 0.971657 |
| q4 | validation | none | 1072 | 35 | 211 | 0.032649 | 0.816231 |
| corner_q3_q4 | validation | none | 571 | 24 | 211 | 0.042032 | 1.050788 |
| corner_rank13_21 | validation | none | 481 | 18 | 209 | 0.037422 | 0.935551 |
| avoid_neighbor_q5 | validation | none | 4163 | 164 | 211 | 0.039395 | 0.984867 |
| q4 | confirmation | none | 1076 | 47 | 210 | 0.043680 | 1.092007 |
| corner_q3_q4 | confirmation | none | 357 | 19 | 190 | 0.053221 | 1.330532 |
| corner_rank13_21 | confirmation | none | 269 | 11 | 179 | 0.040892 | 1.022305 |
| avoid_neighbor_q5 | confirmation | none | 4197 | 168 | 211 | 0.040029 | 1.000715 |

## Square 20 attribution check

| candidate | split | exclusion | observations | wins | rounds | win_rate | lift_vs_uniform |
| --- | --- | --- | --- | --- | --- | --- | --- |
| q4 | all | none | 4284 | 164 | 842 | 0.038282 | 0.957049 |
| corner_q3_q4 | all | none | 2022 | 80 | 818 | 0.039565 | 0.989120 |
| corner_rank13_21 | all | none | 1672 | 59 | 797 | 0.035287 | 0.882177 |
| q4 | development | none | 2136 | 82 | 421 | 0.038390 | 0.959738 |
| corner_q3_q4 | development | none | 1094 | 37 | 417 | 0.033821 | 0.845521 |
| corner_rank13_21 | development | none | 922 | 30 | 409 | 0.032538 | 0.813449 |
| q4 | validation | none | 1072 | 35 | 211 | 0.032649 | 0.816231 |
| corner_q3_q4 | validation | none | 571 | 24 | 211 | 0.042032 | 1.050788 |
| corner_rank13_21 | validation | none | 481 | 18 | 209 | 0.037422 | 0.935551 |
| q4 | confirmation | none | 1076 | 47 | 210 | 0.043680 | 1.092007 |
| corner_q3_q4 | confirmation | none | 357 | 19 | 190 | 0.053221 | 1.330532 |
| corner_rank13_21 | confirmation | none | 269 | 11 | 179 | 0.040892 | 1.022305 |
| q4 | all | exclude_square_20 | 4090 | 157 | 841 | 0.038386 | 0.959658 |
| corner_q3_q4 | all | exclude_square_20 | 1510 | 58 | 786 | 0.038411 | 0.960265 |
| corner_rank13_21 | all | exclude_square_20 | 1241 | 42 | 752 | 0.033844 | 0.846092 |
| q4 | development | exclude_square_20 | 1987 | 78 | 420 | 0.039255 | 0.981379 |
| corner_q3_q4 | development | exclude_square_20 | 808 | 28 | 410 | 0.034653 | 0.866337 |
| corner_rank13_21 | development | exclude_square_20 | 659 | 21 | 397 | 0.031866 | 0.796662 |
| q4 | validation | exclude_square_20 | 1055 | 35 | 211 | 0.033175 | 0.829384 |
| corner_q3_q4 | validation | exclude_square_20 | 462 | 17 | 210 | 0.036797 | 0.919913 |
| corner_rank13_21 | validation | exclude_square_20 | 393 | 13 | 206 | 0.033079 | 0.826972 |
| q4 | confirmation | exclude_square_20 | 1048 | 44 | 210 | 0.041985 | 1.049618 |
| corner_q3_q4 | confirmation | exclude_square_20 | 240 | 13 | 166 | 0.054167 | 1.354167 |
| corner_rank13_21 | confirmation | exclude_square_20 | 189 | 8 | 149 | 0.042328 | 1.058201 |

## Corner q3/q4 by individual square

| square_index | split | observations | wins | rounds | mean_miners | mean_rank | win_rate | lift_vs_uniform |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | confirmation | 79 | 5 | 79 | 139.607595 | 12.835443 | 0.063291 | 1.582278 |
| 0 | development | 338 | 7 | 338 | 143.497041 | 14.698225 | 0.020710 | 0.517751 |
| 0 | validation | 173 | 6 | 173 | 138.763006 | 13.670520 | 0.034682 | 0.867052 |
| 4 | confirmation | 28 | 0 | 28 | 132.821429 | 12.500000 | 0.000000 | 0.000000 |
| 4 | development | 184 | 7 | 184 | 141.918478 | 12.625000 | 0.038043 | 0.951087 |
| 4 | validation | 172 | 9 | 172 | 138.668605 | 14.709302 | 0.052326 | 1.308140 |
| 20 | confirmation | 117 | 6 | 117 | 140.136752 | 14.333333 | 0.051282 | 1.282051 |
| 20 | development | 286 | 9 | 286 | 142.758741 | 16.356643 | 0.031469 | 0.786713 |
| 20 | validation | 109 | 7 | 109 | 138.247706 | 14.422018 | 0.064220 | 1.605505 |
| 24 | confirmation | 133 | 8 | 133 | 139.887218 | 16.563910 | 0.060150 | 1.503759 |
| 24 | development | 286 | 14 | 286 | 143.178322 | 17.206294 | 0.048951 | 1.223776 |
| 24 | validation | 117 | 2 | 117 | 139.076923 | 18.256410 | 0.017094 | 0.427350 |

## Time-decile stability

| candidate | split | exclusion | observations | wins | rounds | win_rate | lift_vs_uniform | round_sequence_min | round_sequence_max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| q4 | decile_01 | none | 407 | 15 | 85 | 0.036855 | 0.921376 | 0 | 84 |
| corner_q3_q4 | decile_01 | none | 224 | 9 | 83 | 0.040179 | 1.004464 | 0 | 84 |
| corner_rank13_21 | decile_01 | none | 218 | 9 | 83 | 0.041284 | 1.032110 | 0 | 84 |
| avoid_neighbor_q5 | decile_01 | none | 1681 | 67 | 85 | 0.039857 | 0.996431 | 0 | 84 |
| q4 | decile_02 | none | 441 | 17 | 85 | 0.038549 | 0.963719 | 85 | 169 |
| corner_q3_q4 | decile_02 | none | 232 | 6 | 85 | 0.025862 | 0.646552 | 85 | 169 |
| corner_rank13_21 | decile_02 | none | 183 | 4 | 84 | 0.021858 | 0.546448 | 85 | 169 |
| avoid_neighbor_q5 | decile_02 | none | 1684 | 67 | 85 | 0.039786 | 0.994656 | 85 | 169 |
| q4 | decile_03 | none | 442 | 20 | 84 | 0.045249 | 1.131222 | 170 | 254 |
| corner_q3_q4 | decile_03 | none | 243 | 8 | 85 | 0.032922 | 0.823045 | 170 | 254 |
| corner_rank13_21 | decile_03 | none | 190 | 6 | 84 | 0.031579 | 0.789474 | 170 | 254 |
| avoid_neighbor_q5 | decile_03 | none | 1682 | 67 | 85 | 0.039834 | 0.995838 | 170 | 254 |
| q4 | decile_04 | none | 437 | 12 | 85 | 0.027460 | 0.686499 | 255 | 339 |
| corner_q3_q4 | decile_04 | none | 245 | 9 | 84 | 0.036735 | 0.918367 | 255 | 339 |
| corner_rank13_21 | decile_04 | none | 209 | 7 | 81 | 0.033493 | 0.837321 | 255 | 339 |
| avoid_neighbor_q5 | decile_04 | none | 1684 | 67 | 85 | 0.039786 | 0.994656 | 255 | 339 |
| q4 | decile_05 | none | 423 | 18 | 85 | 0.042553 | 1.063830 | 340 | 424 |
| corner_q3_q4 | decile_05 | none | 157 | 5 | 83 | 0.031847 | 0.796178 | 340 | 424 |
| corner_rank13_21 | decile_05 | none | 127 | 4 | 80 | 0.031496 | 0.787402 | 340 | 424 |
| avoid_neighbor_q5 | decile_05 | none | 1691 | 60 | 85 | 0.035482 | 0.887049 | 340 | 424 |
| q4 | decile_06 | none | 434 | 18 | 85 | 0.041475 | 1.036866 | 425 | 509 |
| corner_q3_q4 | decile_06 | none | 196 | 12 | 85 | 0.061224 | 1.530612 | 425 | 509 |
| corner_rank13_21 | decile_06 | none | 163 | 10 | 83 | 0.061350 | 1.533742 | 425 | 509 |
| avoid_neighbor_q5 | decile_06 | none | 1676 | 73 | 85 | 0.043556 | 1.088902 | 425 | 509 |
| q4 | decile_07 | none | 425 | 10 | 85 | 0.023529 | 0.588235 | 510 | 594 |
| corner_q3_q4 | decile_07 | none | 254 | 7 | 85 | 0.027559 | 0.688976 | 510 | 594 |
| corner_rank13_21 | decile_07 | none | 220 | 5 | 85 | 0.022727 | 0.568182 | 510 | 594 |
| avoid_neighbor_q5 | decile_07 | none | 1679 | 58 | 85 | 0.034544 | 0.863609 | 510 | 594 |
| q4 | decile_08 | none | 427 | 18 | 84 | 0.042155 | 1.053864 | 595 | 679 |
| corner_q3_q4 | decile_08 | none | 221 | 10 | 82 | 0.045249 | 1.131222 | 595 | 679 |
| corner_rank13_21 | decile_08 | none | 180 | 6 | 81 | 0.033333 | 0.833333 | 595 | 679 |
| avoid_neighbor_q5 | decile_08 | none | 1685 | 63 | 85 | 0.037389 | 0.934718 | 595 | 679 |
| q4 | decile_09 | none | 445 | 20 | 85 | 0.044944 | 1.123596 | 680 | 764 |
| corner_q3_q4 | decile_09 | none | 144 | 10 | 80 | 0.069444 | 1.736111 | 680 | 764 |
| corner_rank13_21 | decile_09 | none | 106 | 6 | 76 | 0.056604 | 1.415094 | 680 | 764 |
| avoid_neighbor_q5 | decile_09 | none | 1689 | 69 | 85 | 0.040853 | 1.021314 | 680 | 764 |
| q4 | decile_10 | none | 403 | 16 | 79 | 0.039702 | 0.992556 | 765 | 843 |
| corner_q3_q4 | decile_10 | none | 106 | 4 | 66 | 0.037736 | 0.943396 | 765 | 843 |
| corner_rank13_21 | decile_10 | none | 76 | 2 | 60 | 0.026316 | 0.657895 | 765 | 843 |
| avoid_neighbor_q5 | decile_10 | none | 1571 | 66 | 79 | 0.042011 | 1.050286 | 765 | 843 |

## Interpretation rules

- A candidate should not advance if lift appears only in development.
- A corner result should not advance if square 20 explains most of it.
- A candidate should appear across multiple time segments.
- Small subgroups remain exploratory even when lift is large.
- Newly observed rounds should remain untouched confirmation data.
