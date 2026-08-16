# Finding 003 — RQ-003 Experiment 2C Miner Count Ordering Characterization

## Status and scope

- Experiment: RQ-003 Experiment 2C — Miner Count Ordering Characterization
- Governing source commit:
  `2fa752a98da4621572fb35c3fcbc7421c5a0eea8`
- Execution validity: **Valid**
- Execution profile: `outcome_blind_characterization_v1`
- Interpretation scope: ordering characterization only

This finding analyzes only:

- the [Experiment 2C protocol](../experiments/rq003-experiment-002c-miner-count-characterization.md);
- the [RQ-003 Research Execution Specification v2](../specifications/rq003-research-execution-specification-v2.md); and
- the sealed [first official Experiment 2C artifacts](../../../data/research/analyses/rq003/experiment-002c-miner-count-characterization/first-official-2fa752a/).

It does not reopen Replay inputs, rerun the experiment, access outcomes,
evaluate prediction, compare baselines, or interpret ordering differences as
winning-square information.

## 1. Execution validity

The first official execution is scientifically valid under the governing
protocol because:

- source commit `2fa752a98da4621572fb35c3fcbc7421c5a0eea8` bound the approved protocol,
  Research Execution Specification v2, and implementation;
- replay dataset SHA-256
  `7680856bc6a01f9b69be0921d6e66b3f43d5241a38e63b37871b6925c1d59ba7`
  matched the protocol binding;
- Replay identity
  `dbd08e16db7589162f436210b9a4d0a61d3b12f97129ca53d9e55cf687a06bcf`
  reconstructed from its immutable first-order bindings;
- audit-manifest identity
  `b4bda415fb0e40bf62f2dd5dd181edb5099cbcfc5031f67d013eb5c80aed927c`
  reconstructed successfully;
- all eight declared artifacts passed canonical encoding, content identity,
  dependency, record-count, digest, and reconstruction validation;
- population accounting preserved every Replay round in canonical order;
- the conformance artifact records `passed` and deterministic reconstruction
  as `validated`; and
- the terminal manifest records outcome access as
  `prohibited_and_not_performed` and the outcome-aware extension as `absent`.

The sealed artifacts contain no winner, label, outcome authorization, outcome
join, MRR, baseline, predictive evaluation, Strategy result, or economic
result.

## 2. Population

| Population disposition | Decisions | Share of Replay |
| --- | ---: | ---: |
| Replay rounds | 18,653 | 100% |
| Eligible decisions | 17,912 | 96.0274% |
| Excluded decisions | 741 | 3.9726% |

The accounting is exact: `17,912 + 741 = 18,653`.

All 741 exclusions have the single predeclared disposition
`incomplete_lifecycle`. No decision was excluded because of outcome presence,
absence, value, provenance, or capture mode. Every eligible round contributes
one decision selected at the governed `end_slot - 5` boundary.

## 3. Ordering characterization

Miner Count is compared independently with raw Deployment and Deployment per
Miner. All ranks are exact descending average ranks; candidate identity does
not break ties.

### 3.1 Miner Count versus raw Deployment

#### Average-rank-vector classes

| Classification | Decisions | Proportion |
| --- | ---: | ---: |
| Identical average-rank vectors | 0 | 0% |
| Tie-only changes | 0 | 0% |
| Strict ordering changes | 17,912 | 100% |

Every eligible decision contains at least one strict Miner Count versus raw
Deployment reversal.

#### Pairwise divergence

There are 300 unordered candidate pairs per decision.

- Pairwise sign disagreements range from 53 to 262.
- Mean disagreement is approximately `163.1639` pairs, or `54.3880%` of all
  candidate pairs; the median is 164.
- Strict reversals range from 36 to 248.
- Mean strict reversals are approximately `140.1154` pairs, or `46.7051%` of
  all pairs; the median is 140.
- Miner Count tie-to-Deployment-strict changes range from 4 to 66, with mean
  approximately `23.0485` and median 22.
- No Miner Count strict relation becomes a raw Deployment tie.

Thus every disagreement is accounted for by either a strict reversal or a
Miner Count tie that raw Deployment resolves strictly.

#### Rank displacement

- Total absolute rank displacement ranges from 71 to 312, with mean
  approximately `209.7407` and median 211.
- Mean absolute displacement per candidate ranges from `71 / 25` to
  `312 / 25`, with population mean approximately `8.3896` ranks.
- The maximum candidate displacement within one decision ranges from `15 / 2`
  to 24, with mean approximately `20.3472` and median 21.
- Across all 447,800 candidate instances, displacement ranges from 0 to 24.

#### Top-k membership

Top-k membership uses exact average rank `<= k`; ties are not broken to force
exactly `k` members.

| Boundary | Decisions with membership change | Proportion |
| --- | ---: | ---: |
| Top 1 | 17,147 | 95.7291% |
| Top 3 | 17,892 | 99.8883% |
| Top 5 | 17,908 | 99.9777% |

The differing sizes of some Miner Count and Deployment Top-k sets are a direct
consequence of average-rank tie semantics, not an identity tie-breaker.

### 3.2 Miner Count versus Deployment per Miner

#### Average-rank-vector classes

| Classification | Decisions | Proportion |
| --- | ---: | ---: |
| Identical average-rank vectors | 0 | 0% |
| Tie-only changes | 0 | 0% |
| Strict ordering changes | 17,912 | 100% |

Every eligible decision contains at least one strict Miner Count versus
Deployment-per-Miner reversal.

#### Pairwise divergence

- Pairwise sign disagreements range from 128 to 300.
- Mean disagreement is approximately `255.9071` pairs, or `85.3024%` of all
  candidate pairs; the median is 260.
- Strict reversals range from 108 to 290.
- Mean strict reversals are approximately `232.8586` pairs, or `77.6195%` of
  all pairs; the median is 237.
- Miner Count tie-to-Deployment-per-Miner-strict changes range from 4 to 66,
  with mean approximately `23.0485` and median 22.
- No Miner Count strict relation becomes a Deployment-per-Miner tie.

The larger divergence from Deployment per Miner than from raw Deployment is
an observed ordering fact. It is not a statement about relative scientific or
predictive quality.

#### Rank displacement

- Total absolute rank displacement ranges from 161 to 312, with mean
  approximately `289.2349` and median 295.
- Mean absolute displacement per candidate ranges from `161 / 25` to
  `312 / 25`, with population mean approximately `11.5694` ranks.
- The maximum candidate displacement within one decision ranges from `31 / 2`
  to 24, with mean approximately `23.6060`; the median and mode are both 24.
- Across all 447,800 candidate instances, displacement ranges from 0 to 24.

#### Top-k membership

| Boundary | Decisions with membership change | Proportion |
| --- | ---: | ---: |
| Top 1 | 17,876 | 99.7990% |
| Top 3 | 17,912 | 100% |
| Top 5 | 17,912 | 100% |

### 3.3 Tie statistics

Miner Count has a materially different tie structure from both reference
orderings:

- every eligible Miner Count ordering contains ties;
- between 8 and 25 candidates participate in Miner Count ties per decision,
  with mean approximately `19.7533` and median 20;
- Miner Count produces between 7 and 21 tie groups, with mean approximately
  `12.0485` and median 12;
- its largest tie group ranges from 2 to 11 candidates, with mean approximately
  `4.7357` and median 5; and
- it produces between 2 and 11 non-singleton groups per decision, with mean
  approximately `6.8018`.

Raw Deployment and Deployment per Miner are each tie-free in 17,911 decisions.
Each has exactly one decision with one two-candidate tie. Consequently, the
reference orderings resolve many Miner Count ties, while neither reference
introduces a tie where Miner Count was strict.

## 4. Board characterization

The outcome-blind board reports show:

- all 17,912 eligible decisions have positive deployment and positive Miner
  Count on all 25 squares;
- positive per-square Miner Count range varies from 6 to 34, with mode 14;
- summed per-square miner memberships range from 2,108 to 4,190 across 1,740
  distinct values, with mode 3,012;
- protocol-published `round.total_miners` ranges from 100 to 183 across 83
  distinct values, with mode 145;
- total deployed lamports range from `3,133,826,987` to `27,386,925,325`, and
  all 17,912 totals are distinct;
- raw Deployment has 25 singleton groups in 17,911 decisions and one
  two-candidate tie in the remaining decision; and
- Deployment per Miner has the same aggregate tie-count pattern.

Both comparisons belong to the strict-ordering-change class in every eligible
decision. The board tables therefore describe variation within that class;
they cannot support a between-class explanation of ordering changes.

## 5. Control verification

| Control | Result | Artifact evidence |
| --- | --- | --- |
| Outcome blindness | Passed | Terminal disposition is `prohibited_and_not_performed`; the outcome-aware extension is absent. |
| Chronology | Passed | Population dispositions preserve canonical Replay order and the single predeclared decision boundary. |
| Protocol revision | Passed | Homogeneous revision `3112ab78a64f92892a70d5d4cbd17e1d14b1c2fe` is validation provenance only. |
| Deterministic execution | Passed | Conformance records deterministic reconstruction as `validated`. |
| Execution profile | Passed | Manifest binds `outcome_blind_characterization_v1`, identity `0ee29e9c2382e2e3ea8e777760a7782f67b123d14402f8cc5be2a25a4d7c41ba`. |
| Canonical reconstruction | Passed | All eight declared artifacts independently reconstructed. |
| Population accounting | Passed | 17,912 eligible plus 741 excluded equals 18,653 Replay rounds. |

## 6. Scientific interpretation

### Miner Count versus raw Deployment

Miner Count ordering is empirically distinct from raw Deployment ordering in
the characterized population. Every eligible decision contains strict
reordering, mean pairwise disagreement exceeds half of all candidate pairs,
mean candidate rank displacement is approximately 8.39 positions, and Top-3
or Top-5 membership changes in more than 99.8% of decisions.

### Miner Count versus Deployment per Miner

Miner Count ordering is also empirically distinct from Deployment-per-Miner
ordering, with greater observed divergence than in the raw Deployment
comparison. Every eligible decision contains strict reordering, mean pairwise
disagreement is approximately 85.30% of candidate pairs, mean candidate rank
displacement is approximately 11.57 positions, and Top-3 and Top-5 membership
change in every eligible decision.

These conclusions establish ordering difference only. The artifacts contain
no evidence about whether Miner Count, raw Deployment, or Deployment per Miner
ranks an eventual winning square better.

## 7. Signal-discovery roadmap implications

Finding 003 completes the missing direct participant-state comparator. It
shows that Miner Count contributes a contemporaneous ordering that is neither
an empirical duplicate of raw Deployment nor of Deployment per Miner, and it
documents substantial Miner Count tie structure that both reference orderings
mostly resolve.

The bounded implications for the three proposed relationship measurements
are:

1. **Signed deployment–miner share imbalance — priority increases in evidentiary
   strength and remains first.** Miner Count and Deployment demonstrably carry
   different within-board orderings, so a signed distributional disagreement
   remains scientifically distinct enough to justify mathematical review and
   outcome-blind characterization. Experiment 2C does not establish the
   candidate's actual ordering or usefulness.
2. **Joint deployment–miner intensity — priority increases in evidentiary
   strength and remains high.** The inputs are not empirically redundant, so
   their joint magnitude cannot be dismissed as merely repeating one observed
   ordering. Experiment 2C does not characterize the product ordering.
3. **Deployment–miner rank consensus — priority increases in evidentiary
   strength and remains high.** The large ordering divergence and heavy Miner
   Count tie structure make an exact tie-aware combination of the two rank
   vectors a scientifically distinct characterization target. Experiment 2C
   does not determine the consensus ranks.

No priority decrease is supported for any of the three candidates. The
artifacts also do not compare those candidates with one another, so Finding
003 does not justify changing their existing relative order. Each still
requires its own mathematical non-equivalence review and outcome-blind
characterization before any predictive evaluation is considered.
