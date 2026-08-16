# RQ-003 Finding 002 — Deployment-per-Miner Ordering Characterization

## 1. Scope and authority

This finding analyzes only the valid first official execution of
[RQ-003 Experiment 2A](../experiments/rq003-experiment-002a-deployment-per-miner-characterization.md),
under the
[RQ-003 Research Execution Specification v2](../specifications/rq003-research-execution-specification-v2.md)
and execution profile `outcome_blind_characterization_v1`.

The analysis uses only the sealed Experiment 2A artifacts in
`data/research/analyses/rq003/experiment-002a-deployment-per-miner-characterization/first-official-7f3a9d8/`.
It does not reopen Replay inputs, access outcomes, evaluate prediction, or
interpret the characterization as evidence about winning squares.

## 2. Execution validity

The execution is scientifically valid under the governing protocol because:

- source commit `7f3a9d875e8a52b184abe4f0ef25f7e2cd6c1799` bound the approved protocol,
  Research Execution Specification v2, and implementation;
- replay dataset SHA-256
  `7680856bc6a01f9b69be0921d6e66b3f43d5241a38e63b37871b6925c1d59ba7`
  matched the protocol binding;
- Replay identity
  `2f69bc29607259bae7a8308ca5517f529194449b2d363b853166f342d2063600`
  reconstructed from its first-order bindings;
- audit-manifest identity
  `101666cb04ff21fe7837d133d54c59446c1de4708456b134032cc3c1677bf333`
  reconstructed successfully;
- population, artifact, provenance, and identity accounting validated;
- the conformance artifact records `passed` and deterministic reconstruction
  as `validated`; and
- the terminal manifest records outcome access as
  `prohibited_and_not_performed` and the outcome-aware extension as absent.

The independent post-execution validator reconstructed all 11 declared
artifacts. No outcome source, outcome authorization, label, outcome join,
baseline, realized MRR, or predictive evaluation participated in the
execution or this finding.

## 3. Population

| Population | Count | Share of Replay rounds |
| --- | ---: | ---: |
| Replay rounds | 18,653 | 100% |
| Eligible decisions | 17,912 | 96.0274% |
| Excluded decisions | 741 | 3.9726% |

The accounting is complete: `17,912 + 741 = 18,653`. Every excluded round has
the single explicit disposition `incomplete_lifecycle`; there are no other
exclusion reasons. Ordered population dispositions span round references
`342063` through `362956` and preserve the Replay ordering.

## 4. Ordering characterization

### 4.1 Average-rank-vector classes

| Classification | Decisions | Proportion |
| --- | ---: | ---: |
| Identical average-rank vectors | 0 | 0 |
| Tie-only changes | 0 | 0 |
| Strict ordering changes | 17,912 | 1 |

Deployment per Miner therefore changed at least one strict candidate relation
in every eligible decision. The artifact contains no unchanged or tie-only
decision.

### 4.2 Pairwise divergence

There are 300 unordered candidate pairs per decision.

- Pairwise sign disagreements ranged from 15 to 235.
- The exact mean was `1,661,217 / 17,912`, approximately `92.7432` pairs or
  `30.9144%` of the 300 pairs.
- The median was 86 disagreements.
- The mode was 77 disagreements, occurring in 243 decisions.
- Every disagreement was a strict reversal: the strict-reversal distribution
  is identical to the disagreement distribution.
- Tie-to-strict and strict-to-tie changes were both zero in all 17,912
  decisions.

### 4.3 Rank displacement

- Total absolute rank displacement per decision ranged from 28 to 308.
- Its exact mean was `601,457 / 4,478`, approximately `134.3138`; its median
  was 126 and its mode was 118, occurring in 364 decisions.
- Mean absolute displacement per candidate ranged from `28 / 25` to
  `308 / 25`, with population mean `601,457 / 111,950`, approximately
  `5.3726` ranks per candidate.
- Maximum candidate displacement within a decision ranged from 3 to 24. Its
  exact mean was `270,937 / 17,912`, approximately `15.1260`; its median was
  15.
- Across all 447,800 candidate instances, absolute displacement ranged from 0
  to 24. Exactly 40,650 candidate instances had zero displacement; the
  remaining 407,150 changed rank.

### 4.4 Top-k membership

| Membership boundary | Decisions changed | Decisions unchanged | Change proportion |
| --- | ---: | ---: | ---: |
| Top 1 | 11,647 | 6,265 | 65.0234% |
| Top 3 | 16,258 | 1,654 | 90.7660% |
| Top 5 | 16,559 | 1,353 | 92.4464% |

### 4.5 Ties and the empty-square extension

Raw deployment and Deployment per Miner each produced 25 tie groups in 17,911
decisions and 24 tie groups in one decision. The largest tie group was one in
17,911 decisions and two in one decision. No relation changed between tied and
strict status.

The canonical `0 / 1` empty-square extension was used by zero candidate
instances in zero decisions. All 447,800 characterized candidate instances
therefore used the ordinary positive-miner rational definition.

## 5. Theoretical upper bound

The per-decision theoretical bound `U_r` had:

- 160 distinct exact values;
- minimum `1 / 56`;
- maximum `24 / 25`;
- median `2 / 3`;
- mode `1 / 2`, occurring in 2,285 decisions; and
- no zero-valued decisions.

The aggregate bound is:

```text
U = 8,866,291,256,533 / 14,985,148,077,900
  ≈ 0.5916719148
```

Under the protocol, `U_r` asks how large the reciprocal-rank improvement could
be if each candidate were treated in turn as a hypothetical winner. `U` is the
mean of those decision-level maxima. It measures the maximum directional
effect made possible by the observed rank-vector differences. It is not
realized MRR, does not use a winning square, and does not establish predictive
performance.

## 6. Board characterization

The predeclared outcome-blind board tables report:

- all 17,912 eligible decisions had positive deployment on all 25 squares;
- all 17,912 had positive miner counts on all 25 squares;
- total deployed lamports ranged from `3,133,826,987` to `27,386,925,325`,
  with all 17,912 totals distinct;
- summed per-square miner memberships ranged from 2,108 to 4,190 across 1,740
  distinct values; the mode was 3,012, occurring 38 times;
- protocol-published `round.total_miners` ranged from 100 to 183 across 83
  distinct values; the mode was 145, occurring 566 times;
- the positive per-square miner-count range varied from 6 to 34; the mode was
  14, occurring 2,379 times; and
- raw deployment had 25 singleton tie groups in 17,911 decisions and 24 groups
  with one two-square tie in one decision.

Every eligible decision belongs to the strict-ordering-change class.
Consequently, the board tables describe variation within that class but cannot
support a between-class comparison. No outcome relationship is computed or
implied.

## 7. Control verification

| Control | Result | Evidence |
| --- | --- | --- |
| Outcome blindness | Passed | Terminal manifest records `prohibited_and_not_performed`; no outcome-aware extension exists. |
| Chronology | Passed | Ordered dispositions preserve canonical Replay order; one predeclared decision boundary is used per eligible round. |
| Protocol revision | Passed | Homogeneous protocol source revision `3112ab78a64f92892a70d5d4cbd17e1d14b1c2fe` is validation provenance only. |
| Deterministic execution | Passed | Conformance records deterministic reconstruction as validated. |
| Execution profile | Passed | Manifest binds `outcome_blind_characterization_v1`. |
| Canonical reconstruction | Passed | All 11 declared artifacts and their dependency identities reconstructed. |
| Population accounting | Passed | 17,912 eligible plus 741 explicitly excluded rounds equals 18,653 Replay rounds. |

## 8. Scientific interpretation

Yes. Deployment per Miner materially changes candidate ordering relative to
raw deployed lamports in this characterized population.

This conclusion follows only from the protocol's descriptive ordering
measures: all eligible decisions exhibit strict reversals; the minimum
decision has 15 reversed pairwise relations and total absolute rank
displacement of 28; and Top-1, Top-3, and Top-5 membership changes occur in
65.0234%, 90.7660%, and 92.4464% of eligible decisions, respectively.

This is an ordering-characterization result. It makes no claim about winning
squares or predictive value.

## 9. Governance recommendation

Finding 002 supplies the characterization information required for governance
to consider Experiment 2B: complete rank-vector classes, divergence and
displacement distributions, Top-k changes, tie and empty-square statistics,
board-characteristic tables, and the exact theoretical bound `U`.

It does not authorize Experiment 2B. No prospective `delta_min` or governance
identity exists, and this finding neither selects one nor retroactively applies
one. The recorded continuation disposition therefore remains
`research_governance_decision_required` and `experiment_2b_authorized` remains
false.
