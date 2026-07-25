# RFC-002B: Stability and Attribution

## Status

Chronological validation analysis. No live strategy authorization.

## Dataset

- Path: `data/research/square_features_v1_slots_20.csv`
- SHA-256: `5c4cadae157684e5dae994b9e2c4032d7e980e77c87bd7c58e61c08d96167b6d`
- Rows: 10925
- Rounds: 437
- Chronology column: `start_slot`

## Split design

- Development: first 50% of rounds
- Validation: next 25% of rounds
- Confirmation: final 25% of rounds

## Candidate stability by split

| candidate | split | exclusion | observations | wins | rounds | win_rate | lift_vs_uniform |
| --- | --- | --- | --- | --- | --- | --- | --- |
| q4 | development | none | 1080 | 51 | 217 | 0.047222 | 1.180556 |
| corner_q3_q4 | development | none | 491 | 35 | 214 | 0.071283 | 1.782077 |
| corner_rank13_21 | development | none | 424 | 31 | 210 | 0.073113 | 1.827830 |
| avoid_neighbor_q5 | development | none | 4317 | 178 | 218 | 0.041232 | 1.030808 |
| q4 | validation | none | 554 | 21 | 109 | 0.037906 | 0.947653 |
| corner_q3_q4 | validation | none | 295 | 14 | 109 | 0.047458 | 1.186441 |
| corner_rank13_21 | validation | none | 233 | 8 | 107 | 0.034335 | 0.858369 |
| avoid_neighbor_q5 | validation | none | 2157 | 91 | 109 | 0.042188 | 1.054706 |
| q4 | confirmation | none | 565 | 32 | 110 | 0.056637 | 1.415929 |
| corner_q3_q4 | confirmation | none | 286 | 11 | 108 | 0.038462 | 0.961538 |
| corner_rank13_21 | confirmation | none | 230 | 12 | 107 | 0.052174 | 1.304348 |
| avoid_neighbor_q5 | confirmation | none | 2190 | 95 | 110 | 0.043379 | 1.084475 |

## Square 20 attribution check

| candidate | split | exclusion | observations | wins | rounds | win_rate | lift_vs_uniform |
| --- | --- | --- | --- | --- | --- | --- | --- |
| q4 | all | none | 2199 | 104 | 436 | 0.047294 | 1.182356 |
| corner_q3_q4 | all | none | 1072 | 60 | 431 | 0.055970 | 1.399254 |
| corner_rank13_21 | all | none | 887 | 51 | 424 | 0.057497 | 1.437430 |
| q4 | development | none | 1080 | 51 | 217 | 0.047222 | 1.180556 |
| corner_q3_q4 | development | none | 491 | 35 | 214 | 0.071283 | 1.782077 |
| corner_rank13_21 | development | none | 424 | 31 | 210 | 0.073113 | 1.827830 |
| q4 | validation | none | 554 | 21 | 109 | 0.037906 | 0.947653 |
| corner_q3_q4 | validation | none | 295 | 14 | 109 | 0.047458 | 1.186441 |
| corner_rank13_21 | validation | none | 233 | 8 | 107 | 0.034335 | 0.858369 |
| q4 | confirmation | none | 565 | 32 | 110 | 0.056637 | 1.415929 |
| corner_q3_q4 | confirmation | none | 286 | 11 | 108 | 0.038462 | 0.961538 |
| corner_rank13_21 | confirmation | none | 230 | 12 | 107 | 0.052174 | 1.304348 |
| q4 | all | exclude_square_20 | 2076 | 94 | 436 | 0.045279 | 1.131985 |
| corner_q3_q4 | all | exclude_square_20 | 816 | 40 | 427 | 0.049020 | 1.225490 |
| corner_rank13_21 | all | exclude_square_20 | 647 | 34 | 401 | 0.052550 | 1.313756 |
| q4 | development | exclude_square_20 | 1034 | 47 | 217 | 0.045455 | 1.136364 |
| corner_q3_q4 | development | exclude_square_20 | 380 | 25 | 214 | 0.065789 | 1.644737 |
| corner_rank13_21 | development | exclude_square_20 | 319 | 22 | 199 | 0.068966 | 1.724138 |
| q4 | validation | exclude_square_20 | 530 | 20 | 109 | 0.037736 | 0.943396 |
| corner_q3_q4 | validation | exclude_square_20 | 216 | 10 | 107 | 0.046296 | 1.157407 |
| corner_rank13_21 | validation | exclude_square_20 | 169 | 6 | 104 | 0.035503 | 0.887574 |
| q4 | confirmation | exclude_square_20 | 512 | 27 | 110 | 0.052734 | 1.318359 |
| corner_q3_q4 | confirmation | exclude_square_20 | 220 | 5 | 106 | 0.022727 | 0.568182 |
| corner_rank13_21 | confirmation | exclude_square_20 | 159 | 6 | 98 | 0.037736 | 0.943396 |

## Corner q3/q4 by individual square

| square_index | split | observations | wins | rounds | mean_miners | mean_rank | win_rate | lift_vs_uniform |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | confirmation | 87 | 4 | 87 | 150.597701 | 13.344828 | 0.045977 | 1.149425 |
| 0 | development | 166 | 7 | 166 | 135.012048 | 13.710843 | 0.042169 | 1.054217 |
| 0 | validation | 77 | 5 | 77 | 137.519481 | 12.350649 | 0.064935 | 1.623377 |
| 4 | confirmation | 55 | 1 | 55 | 149.581818 | 12.818182 | 0.018182 | 0.454545 |
| 4 | development | 188 | 16 | 188 | 134.085106 | 15.335106 | 0.085106 | 2.127660 |
| 4 | validation | 82 | 3 | 82 | 138.231707 | 15.500000 | 0.036585 | 0.914634 |
| 20 | confirmation | 66 | 6 | 66 | 151.484848 | 18.166667 | 0.090909 | 2.272727 |
| 20 | development | 111 | 10 | 111 | 131.081081 | 15.882883 | 0.090090 | 2.252252 |
| 20 | validation | 79 | 4 | 79 | 136.088608 | 14.860759 | 0.050633 | 1.265823 |
| 24 | confirmation | 78 | 0 | 78 | 151.179487 | 16.576923 | 0.000000 | 0.000000 |
| 24 | development | 26 | 2 | 26 | 130.076923 | 19.769231 | 0.076923 | 1.923077 |
| 24 | validation | 57 | 2 | 57 | 143.877193 | 18.105263 | 0.035088 | 0.877193 |

## Time-decile stability

| candidate | split | exclusion | observations | wins | rounds | win_rate | lift_vs_uniform | round_sequence_min | round_sequence_max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| q4 | decile_01 | none | 215 | 11 | 44 | 0.051163 | 1.279070 | 0 | 43 |
| corner_q3_q4 | decile_01 | none | 73 | 6 | 43 | 0.082192 | 2.054795 | 0 | 43 |
| corner_rank13_21 | decile_01 | none | 71 | 6 | 43 | 0.084507 | 2.112676 | 0 | 43 |
| avoid_neighbor_q5 | decile_01 | none | 865 | 42 | 44 | 0.048555 | 1.213873 | 0 | 43 |
| q4 | decile_02 | none | 205 | 6 | 43 | 0.029268 | 0.731707 | 44 | 87 |
| corner_q3_q4 | decile_02 | none | 96 | 2 | 42 | 0.020833 | 0.520833 | 44 | 87 |
| corner_rank13_21 | decile_02 | none | 95 | 2 | 44 | 0.021053 | 0.526316 | 44 | 87 |
| avoid_neighbor_q5 | decile_02 | none | 869 | 34 | 44 | 0.039125 | 0.978136 | 44 | 87 |
| q4 | decile_03 | none | 231 | 15 | 44 | 0.064935 | 1.623377 | 88 | 131 |
| corner_q3_q4 | decile_03 | none | 129 | 13 | 44 | 0.100775 | 2.519380 | 88 | 131 |
| corner_rank13_21 | decile_03 | none | 118 | 12 | 44 | 0.101695 | 2.542373 | 88 | 131 |
| avoid_neighbor_q5 | decile_03 | none | 872 | 34 | 44 | 0.038991 | 0.974771 | 88 | 131 |
| q4 | decile_04 | none | 219 | 8 | 44 | 0.036530 | 0.913242 | 132 | 175 |
| corner_q3_q4 | decile_04 | none | 92 | 6 | 43 | 0.065217 | 1.630435 | 132 | 175 |
| corner_rank13_21 | decile_04 | none | 66 | 5 | 39 | 0.075758 | 1.893939 | 132 | 175 |
| avoid_neighbor_q5 | decile_04 | none | 876 | 34 | 44 | 0.038813 | 0.970320 | 132 | 175 |
| q4 | decile_05 | none | 217 | 11 | 44 | 0.050691 | 1.267281 | 176 | 219 |
| corner_q3_q4 | decile_05 | none | 105 | 8 | 44 | 0.076190 | 1.904762 | 176 | 219 |
| corner_rank13_21 | decile_05 | none | 77 | 6 | 42 | 0.077922 | 1.948052 | 176 | 219 |
| avoid_neighbor_q5 | decile_05 | none | 875 | 36 | 44 | 0.041143 | 1.028571 | 176 | 219 |
| q4 | decile_06 | none | 224 | 13 | 44 | 0.058036 | 1.450893 | 220 | 263 |
| corner_q3_q4 | decile_06 | none | 117 | 9 | 44 | 0.076923 | 1.923077 | 220 | 263 |
| corner_rank13_21 | decile_06 | none | 97 | 5 | 43 | 0.051546 | 1.288660 | 220 | 263 |
| avoid_neighbor_q5 | decile_06 | none | 874 | 38 | 44 | 0.043478 | 1.086957 | 220 | 263 |
| q4 | decile_07 | none | 226 | 4 | 44 | 0.017699 | 0.442478 | 264 | 307 |
| corner_q3_q4 | decile_07 | none | 119 | 4 | 44 | 0.033613 | 0.840336 | 264 | 307 |
| corner_rank13_21 | decile_07 | none | 91 | 3 | 43 | 0.032967 | 0.824176 | 264 | 307 |
| avoid_neighbor_q5 | decile_07 | none | 866 | 36 | 44 | 0.041570 | 1.039261 | 264 | 307 |
| q4 | decile_08 | none | 226 | 13 | 44 | 0.057522 | 1.438053 | 308 | 351 |
| corner_q3_q4 | decile_08 | none | 134 | 5 | 44 | 0.037313 | 0.932836 | 308 | 351 |
| corner_rank13_21 | decile_08 | none | 112 | 5 | 44 | 0.044643 | 1.116071 | 308 | 351 |
| avoid_neighbor_q5 | decile_08 | none | 874 | 38 | 44 | 0.043478 | 1.086957 | 308 | 351 |
| q4 | decile_09 | none | 219 | 11 | 44 | 0.050228 | 1.255708 | 352 | 395 |
| corner_q3_q4 | decile_09 | none | 104 | 1 | 44 | 0.009615 | 0.240385 | 352 | 395 |
| corner_rank13_21 | decile_09 | none | 93 | 3 | 44 | 0.032258 | 0.806452 | 352 | 395 |
| avoid_neighbor_q5 | decile_09 | none | 878 | 36 | 44 | 0.041002 | 1.025057 | 352 | 395 |
| q4 | decile_10 | none | 217 | 12 | 41 | 0.055300 | 1.382488 | 396 | 436 |
| corner_q3_q4 | decile_10 | none | 103 | 6 | 39 | 0.058252 | 1.456311 | 396 | 436 |
| corner_rank13_21 | decile_10 | none | 67 | 4 | 38 | 0.059701 | 1.492537 | 396 | 436 |
| avoid_neighbor_q5 | decile_10 | none | 815 | 36 | 41 | 0.044172 | 1.104294 | 396 | 436 |

## Interpretation rules

- A candidate should not advance if lift appears only in development.
- A corner result should not advance if square 20 explains most of it.
- A candidate should appear across multiple time segments.
- Small subgroups remain exploratory even when lift is large.
- Newly observed rounds should remain untouched confirmation data.
