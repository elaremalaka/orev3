# RFC-002B: Stability and Attribution

## Status

Chronological validation analysis. No live strategy authorization.

## Dataset

- Path: `data/research/square_features_v2_slots_20.csv`
- SHA-256: `504801ab9cb9948de2cd13622aa9454ff841488d4d13ecb36a9321ed5cc8bbee`
- Rows: 22525
- Rounds: 901
- Chronology column: `start_slot`

## Split design

- Development: first 50% of rounds
- Validation: next 25% of rounds
- Confirmation: final 25% of rounds

## Candidate stability by split

| candidate | split | exclusion | observations | wins | rounds | win_rate | lift_vs_uniform |
| --- | --- | --- | --- | --- | --- | --- | --- |
| q4 | development | none | 2270 | 87 | 449 | 0.038326 | 0.958150 |
| corner_q3_q4 | development | none | 1175 | 39 | 445 | 0.033191 | 0.829787 |
| corner_rank13_21 | development | none | 990 | 32 | 434 | 0.032323 | 0.808081 |
| avoid_neighbor_q5 | development | none | 8923 | 351 | 450 | 0.039337 | 0.983414 |
| q4 | validation | none | 1144 | 41 | 225 | 0.035839 | 0.895979 |
| corner_q3_q4 | validation | none | 583 | 26 | 225 | 0.044597 | 1.114923 |
| corner_rank13_21 | validation | none | 493 | 21 | 223 | 0.042596 | 1.064909 |
| avoid_neighbor_q5 | validation | none | 4444 | 174 | 225 | 0.039154 | 0.978848 |
| q4 | confirmation | none | 1154 | 49 | 225 | 0.042461 | 1.061525 |
| corner_q3_q4 | confirmation | none | 403 | 20 | 205 | 0.049628 | 1.240695 |
| corner_rank13_21 | confirmation | none | 304 | 11 | 194 | 0.036184 | 0.904605 |
| avoid_neighbor_q5 | confirmation | none | 4494 | 179 | 226 | 0.039831 | 0.995772 |

## Square 20 attribution check

| candidate | split | exclusion | observations | wins | rounds | win_rate | lift_vs_uniform |
| --- | --- | --- | --- | --- | --- | --- | --- |
| q4 | all | none | 4568 | 177 | 899 | 0.038748 | 0.968695 |
| corner_q3_q4 | all | none | 2161 | 85 | 875 | 0.039334 | 0.983341 |
| corner_rank13_21 | all | none | 1787 | 64 | 851 | 0.035814 | 0.895355 |
| q4 | development | none | 2270 | 87 | 449 | 0.038326 | 0.958150 |
| corner_q3_q4 | development | none | 1175 | 39 | 445 | 0.033191 | 0.829787 |
| corner_rank13_21 | development | none | 990 | 32 | 434 | 0.032323 | 0.808081 |
| q4 | validation | none | 1144 | 41 | 225 | 0.035839 | 0.895979 |
| corner_q3_q4 | validation | none | 583 | 26 | 225 | 0.044597 | 1.114923 |
| corner_rank13_21 | validation | none | 493 | 21 | 223 | 0.042596 | 1.064909 |
| q4 | confirmation | none | 1154 | 49 | 225 | 0.042461 | 1.061525 |
| corner_q3_q4 | confirmation | none | 403 | 20 | 205 | 0.049628 | 1.240695 |
| corner_rank13_21 | confirmation | none | 304 | 11 | 194 | 0.036184 | 0.904605 |
| q4 | all | exclude_square_20 | 4356 | 170 | 898 | 0.039027 | 0.975666 |
| corner_q3_q4 | all | exclude_square_20 | 1617 | 62 | 843 | 0.038343 | 0.958565 |
| corner_rank13_21 | all | exclude_square_20 | 1324 | 46 | 805 | 0.034743 | 0.868580 |
| q4 | development | exclude_square_20 | 2104 | 83 | 448 | 0.039449 | 0.986217 |
| corner_q3_q4 | development | exclude_square_20 | 858 | 29 | 439 | 0.033800 | 0.844988 |
| corner_rank13_21 | development | exclude_square_20 | 696 | 22 | 421 | 0.031609 | 0.790230 |
| q4 | validation | exclude_square_20 | 1129 | 41 | 225 | 0.036315 | 0.907883 |
| corner_q3_q4 | validation | exclude_square_20 | 487 | 20 | 223 | 0.041068 | 1.026694 |
| corner_rank13_21 | validation | exclude_square_20 | 416 | 16 | 220 | 0.038462 | 0.961538 |
| q4 | confirmation | exclude_square_20 | 1123 | 46 | 225 | 0.040962 | 1.024043 |
| corner_q3_q4 | confirmation | exclude_square_20 | 272 | 13 | 181 | 0.047794 | 1.194853 |
| corner_rank13_21 | confirmation | exclude_square_20 | 212 | 8 | 164 | 0.037736 | 0.943396 |

## Corner q3/q4 by individual square

| square_index | split | observations | wins | rounds | mean_miners | mean_rank | win_rate | lift_vs_uniform |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | confirmation | 91 | 5 | 91 | 139.153846 | 12.967033 | 0.054945 | 1.373626 |
| 0 | development | 355 | 7 | 355 | 143.070423 | 14.543662 | 0.019718 | 0.492958 |
| 0 | validation | 187 | 6 | 187 | 139.513369 | 13.855615 | 0.032086 | 0.802139 |
| 4 | confirmation | 38 | 0 | 38 | 133.684211 | 12.605263 | 0.000000 | 0.000000 |
| 4 | development | 208 | 9 | 208 | 140.841346 | 13.144231 | 0.043269 | 1.081731 |
| 4 | validation | 183 | 11 | 183 | 139.224044 | 14.650273 | 0.060109 | 1.502732 |
| 20 | confirmation | 131 | 7 | 131 | 139.603053 | 14.412214 | 0.053435 | 1.335878 |
| 20 | development | 317 | 10 | 317 | 142.123028 | 16.410095 | 0.031546 | 0.788644 |
| 20 | validation | 96 | 6 | 96 | 138.729167 | 14.343750 | 0.062500 | 1.562500 |
| 24 | confirmation | 143 | 8 | 143 | 139.657343 | 16.699301 | 0.055944 | 1.398601 |
| 24 | development | 295 | 13 | 295 | 143.369492 | 17.084746 | 0.044068 | 1.101695 |
| 24 | validation | 117 | 3 | 117 | 139.675214 | 18.435897 | 0.025641 | 0.641026 |

## Time-decile stability

| candidate | split | exclusion | observations | wins | rounds | win_rate | lift_vs_uniform | round_sequence_min | round_sequence_max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| q4 | decile_01 | none | 438 | 19 | 91 | 0.043379 | 1.084475 | 0 | 90 |
| corner_q3_q4 | decile_01 | none | 210 | 8 | 89 | 0.038095 | 0.952381 | 0 | 90 |
| corner_rank13_21 | decile_01 | none | 186 | 8 | 87 | 0.043011 | 1.075269 | 0 | 90 |
| avoid_neighbor_q5 | decile_01 | none | 1807 | 73 | 91 | 0.040398 | 1.009961 | 0 | 90 |
| q4 | decile_02 | none | 465 | 19 | 91 | 0.040860 | 1.021505 | 91 | 181 |
| corner_q3_q4 | decile_02 | none | 259 | 7 | 91 | 0.027027 | 0.675676 | 91 | 181 |
| corner_rank13_21 | decile_02 | none | 237 | 7 | 89 | 0.029536 | 0.738397 | 91 | 181 |
| avoid_neighbor_q5 | decile_02 | none | 1806 | 73 | 91 | 0.040421 | 1.010520 | 91 | 181 |
| q4 | decile_03 | none | 454 | 17 | 90 | 0.037445 | 0.936123 | 182 | 272 |
| corner_q3_q4 | decile_03 | none | 247 | 8 | 91 | 0.032389 | 0.809717 | 182 | 272 |
| corner_rank13_21 | decile_03 | none | 190 | 6 | 90 | 0.031579 | 0.789474 | 182 | 272 |
| avoid_neighbor_q5 | decile_03 | none | 1807 | 68 | 91 | 0.037631 | 0.940786 | 182 | 272 |
| q4 | decile_04 | none | 474 | 15 | 91 | 0.031646 | 0.791139 | 273 | 363 |
| corner_q3_q4 | decile_04 | none | 286 | 11 | 91 | 0.038462 | 0.961538 | 273 | 363 |
| corner_rank13_21 | decile_04 | none | 239 | 7 | 91 | 0.029289 | 0.732218 | 273 | 363 |
| avoid_neighbor_q5 | decile_04 | none | 1796 | 73 | 91 | 0.040646 | 1.016147 | 273 | 363 |
| q4 | decile_05 | none | 467 | 17 | 91 | 0.036403 | 0.910064 | 364 | 454 |
| corner_q3_q4 | decile_05 | none | 182 | 5 | 88 | 0.027473 | 0.686813 | 364 | 454 |
| corner_rank13_21 | decile_05 | none | 145 | 4 | 82 | 0.027586 | 0.689655 | 364 | 454 |
| avoid_neighbor_q5 | decile_05 | none | 1810 | 68 | 91 | 0.037569 | 0.939227 | 364 | 454 |
| q4 | decile_06 | none | 464 | 20 | 91 | 0.043103 | 1.077586 | 455 | 545 |
| corner_q3_q4 | decile_06 | none | 198 | 11 | 91 | 0.055556 | 1.388889 | 455 | 545 |
| corner_rank13_21 | decile_06 | none | 161 | 10 | 89 | 0.062112 | 1.552795 | 455 | 545 |
| avoid_neighbor_q5 | decile_06 | none | 1800 | 76 | 91 | 0.042222 | 1.055556 | 455 | 545 |
| q4 | decile_07 | none | 456 | 14 | 91 | 0.030702 | 0.767544 | 546 | 636 |
| corner_q3_q4 | decile_07 | none | 265 | 9 | 91 | 0.033962 | 0.849057 | 546 | 636 |
| corner_rank13_21 | decile_07 | none | 230 | 7 | 91 | 0.030435 | 0.760870 | 546 | 636 |
| avoid_neighbor_q5 | decile_07 | none | 1795 | 66 | 91 | 0.036769 | 0.919220 | 546 | 636 |
| q4 | decile_08 | none | 457 | 18 | 90 | 0.039387 | 0.984683 | 637 | 727 |
| corner_q3_q4 | decile_08 | none | 253 | 12 | 90 | 0.047431 | 1.185771 | 637 | 727 |
| corner_rank13_21 | decile_08 | none | 210 | 7 | 90 | 0.033333 | 0.833333 | 637 | 727 |
| avoid_neighbor_q5 | decile_08 | none | 1800 | 67 | 91 | 0.037222 | 0.930556 | 637 | 727 |
| q4 | decile_09 | none | 474 | 20 | 91 | 0.042194 | 1.054852 | 728 | 818 |
| corner_q3_q4 | decile_09 | none | 151 | 10 | 84 | 0.066225 | 1.655629 | 728 | 818 |
| corner_rank13_21 | decile_09 | none | 111 | 6 | 80 | 0.054054 | 1.351351 | 728 | 818 |
| avoid_neighbor_q5 | decile_09 | none | 1810 | 73 | 91 | 0.040331 | 1.008287 | 728 | 818 |
| q4 | decile_10 | none | 419 | 18 | 82 | 0.042959 | 1.073986 | 819 | 900 |
| corner_q3_q4 | decile_10 | none | 110 | 4 | 69 | 0.036364 | 0.909091 | 819 | 900 |
| corner_rank13_21 | decile_10 | none | 78 | 2 | 62 | 0.025641 | 0.641026 | 819 | 900 |
| avoid_neighbor_q5 | decile_10 | none | 1630 | 67 | 82 | 0.041104 | 1.027607 | 819 | 900 |

## Interpretation rules

- A candidate should not advance if lift appears only in development.
- A corner result should not advance if square 20 explains most of it.
- A candidate should appear across multiple time segments.
- Small subgroups remain exploratory even when lift is large.
- Newly observed rounds should remain untouched confirmation data.
