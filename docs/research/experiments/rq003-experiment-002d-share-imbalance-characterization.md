# RQ-003 Experiment 2D — Signed Deployment–Miner Share Imbalance Characterization

## Status

- Research design only.
- Implementation authorized: No.
- Empirical execution authorized: No.
- Outcome access authorized: No.

This document governs the first outcome-blind characterization of a
distribution-relationship measurement under RQ-003. It does not evaluate
winning-square prediction and does not authorize a predictive experiment.

## Authority

This protocol uses only:

- [RQ-003](../questions/RQ-003-winning-square-predictability.md);
- the [RQ-003 Measurement Catalog](../investigations/rq003-measurement-catalog.md);
- the [Feature Eligibility Resolution](../questions/RQ-003-feature-eligibility-resolution.md);
- the [RQ-003 Research Execution Specification v2](../specifications/rq003-research-execution-specification-v2.md);
- [Finding 001](../findings/rq003-experiment-001-analysis.md);
- [Finding 002](../findings/rq003-experiment-002-analysis.md);
- [Finding 003](../findings/rq003-experiment-002c-analysis.md); and
- the [RQ-003 Signal Discovery Roadmap](../investigations/rq003-signal-discovery-roadmap.md).

The experiment binds Research Execution Specification revision
`rq003-research-execution-specification-v2` and execution profile
`outcome_blind_characterization_v1`. The specification owns reusable
identity, provenance, population-accounting, artifact, reconstruction, and
terminal-manifest mechanics. This protocol owns the scientific measurement
and characterization defined below.

## 1. Scientific motivation

The completed participant-state findings establish three bounded facts:

- Finding 001 reports negative evidence for direct descending raw Deployment
  under its governed predictive protocol. This result is specific to that
  direct ordering and does not determine the behavior of a relationship
  between Deployment and Miner Count.
- Finding 002 establishes outcome-blind strict ordering changes between
  Deployment per Miner and raw Deployment in every eligible decision. A
  candidate-varying relationship between the two participant-state quantities
  can therefore produce an empirically distinct ordering.
- Finding 003 establishes outcome-blind strict ordering changes between direct
  Miner Count and both raw Deployment and Deployment per Miner in every
  eligible decision. It also documents substantial Miner Count tie structure
  that the other two orderings mostly resolve.

Together, these findings justify characterizing a relationship between the
complete Deployment and Miner Count distributions rather than another direct
ordering or common-scalar normalization. Signed Deployment–Miner Share
Imbalance measures whether a square carries a greater share of board-wide
Deployment than of board-wide Miner Count, while preserving the direction of
that difference.

The measurement does not assert efficiency, capital quality, participant
intent, economic value, or predictive information.

## 2. Research question

Across eligible frozen replay decisions, does descending Signed
Deployment–Miner Share Imbalance produce a materially different candidate
ordering from:

1. descending raw Deployment;
2. descending Miner Count; and
3. descending Deployment per Miner?

For each comparison, the experiment asks whether exact average-rank vectors
are identical, differ only through ties, or contain strict ordering changes,
and how large the observed differences are.

The experiment does not ask which ordering is better or whether any ordering
predicts the winning square.

## 3. Derived measurement definition

### 3.1 Inputs and board totals

For candidate square `s` in one frozen decision-time observation, let:

- `D_s` be the approved protocol-published per-square deployed lamports;
- `M_s` be the approved protocol-published per-square Miner Count;
- `S_D = sum_j(D_j)` over the 25 canonical squares; and
- `S_M = sum_j(M_j)` over the 25 canonical squares.

`S_M` is the sum of per-square Miner Count memberships. It is not
`round.total_miners` and must not be substituted with the round-wide unique
Miner-authority aggregate.

All 25 `D_s` and all 25 `M_s` values must originate from the same immutable
decision snapshot. Historical observations, supplementary reads,
cross-account repair, and outcome-derived replacement are prohibited.

### 3.2 Signed share imbalance

Define Deployment Share, Miner Share, and Signed Deployment–Miner Share
Imbalance as:

```text
DeploymentShare(s) = D_s / S_D
MinerShare(s)      = M_s / S_M

I_s = DeploymentShare(s) - MinerShare(s)
    = (D_s × S_M - M_s × S_D) / (S_D × S_M)
```

The unit is dimensionless share difference. The sign convention is:

- `I_s > 0`: the square's Deployment share exceeds its Miner Count share;
- `I_s = 0`: the two shares are equal; and
- `I_s < 0`: the square's Deployment share is below its Miner Count share.

The sign is an observed mathematical direction. It is not a favorable or
unfavorable classification.

### 3.3 Zero handling

The rules are exhaustive:

- `S_D > 0` and `S_M > 0` are required;
- if `S_D = 0` or `S_M = 0`, the decision is invalid and fails closed because
  at least one share distribution is undefined;
- candidate-level `D_s = 0`, `M_s = 0`, or both are valid when both board
  totals remain positive; and
- no constant, pseudocount, imputation, smoothing term, or empty-square
  extension may be introduced.

### 3.4 Exact representation and comparison

Represent each `I_s` as one canonical reduced signed rational pair:

```text
(signed_numerator, positive_denominator)
```

where:

- `signed_numerator = D_s × S_M - M_s × S_D`;
- `positive_denominator = S_D × S_M`;
- numerator and denominator are divided by
  `gcd(abs(signed_numerator), positive_denominator)`; and
- zero has the unique canonical representation `0 / 1`.

Comparison uses exact signed integer cross multiplication. Floating-point
division, approximate equality, rounding, normalization after construction,
and candidate-identity tie-breaking are prohibited.

Because the denominator `S_D × S_M` is common and positive for every square
in one decision, an implementation may compare the exact signed numerators
within that decision. The persisted measurement remains the canonical signed
rational so that identity and reconstruction do not depend on an implicit
comparison shortcut.

## 4. Mathematical assessment

### 4.1 Distinction from raw Deployment

Signed Share Imbalance is not a monotonic transformation of `D_s`. Consider a
three-candidate board with `S_D = 100` and `S_M = 100`:

| Candidate | Deployment | Miner Count | Share imbalance |
| --- | ---: | ---: | ---: |
| A | 60 | 60 | `0` |
| B | 40 | 10 | `3 / 10` |
| C | 0 | 30 | `-3 / 10` |

Raw Deployment orders A before B, while Share Imbalance orders B before A.
The candidate-varying Miner Share subtraction can therefore reverse raw
Deployment ordering.

### 4.2 Distinction from Miner Count

The same board proves non-equivalence to Miner Count. Miner Count orders A
before B because `60 > 10`, while Share Imbalance orders B before A because
`3 / 10 > 0`.

### 4.3 Distinction from Deployment per Miner

Signed Share Imbalance is not a monotonic transformation of `D_s / M_s`.
Consider a three-candidate board with `S_D = 100` and `S_M = 100`:

| Candidate | Deployment | Miner Count | Deployment per Miner | Share imbalance |
| --- | ---: | ---: | ---: | ---: |
| A | 10 | 1 | `10` | `9 / 100` |
| B | 80 | 40 | `2` | `2 / 5` |
| C | 10 | 59 | `10 / 59` | `-49 / 100` |

Deployment per Miner orders A before B, while Share Imbalance orders B before
A. Share Imbalance weights each square's local Deployment-per-Miner departure
from the board-wide ratio by its Miner Share; it is not order-equivalent to
the local ratio.

### 4.4 Assessment disposition

No governed comparison is algebraically equivalent. All three comparisons
therefore proceed to outcome-blind characterization. These proofs establish
mathematical possibility only; they do not establish that reordering occurs
in the governed Replay population.

## 5. Population and immutable bindings

Experiment 2D reuses the outcome-blind population framework established by
the valid Experiment 2A and Experiment 2C executions. The source is the same
immutable replay dataset; a byte-different source is a different population
and cannot be substituted silently.

A conformant execution must bind:

- replay dataset version `replay-dataset-v1`;
- replay dataset SHA-256
  `7680856bc6a01f9b69be0921d6e66b3f43d5241a38e63b37871b6925c1d59ba7`;
- protocol revision identity
  `3112ab78a64f92892a70d5d4cbd17e1d14b1c2fe` as validation provenance only;
- Research Execution Specification revision
  `rq003-research-execution-specification-v2`;
- execution profile `outcome_blind_characterization_v1`;
- the immutable Experiment 2D protocol and configuration identities;
- the frozen implementation source-commit provenance identity;
- the immutable decision-selection configuration identity;
- canonical replay-round order by ascending immutable round chronology, with
  `round_id` as the deterministic tie-breaker; and
- canonical candidate order `0` through `24` within each decision.

The protocol document digest and implementation source commit must be bound
prospectively when implementation is frozen. Replay identity is derived rather
than embedded. It must reconstruct from the bound execution specification,
execution profile, experiment configuration, source commit, replay dataset,
decision-selection configuration, and ordered Replay population.

There is one decision per replay round: the latest valid observation at or
before `end_slot - 5`. A decision is eligible only when:

1. the replay lifecycle is complete;
2. the frozen decision observation is valid;
3. the Deployment and Miner Count fundamental measurements reconstruct and
   conform for all 25 candidates;
4. `S_D > 0` and `S_M > 0`;
5. all four governed orderings cover the same 25 canonical candidates;
6. the Deployment-per-Miner reference satisfies its governed exact rational
   and zero rules; and
7. the protocol revision is supported and homogeneous within the population.

Every excluded decision must receive exactly one deterministic pre-outcome
disposition. Outcome presence, absence, value, provenance, and capture mode
must not affect eligibility.

## 6. Ordering procedures

For every eligible decision, construct exactly four orderings over the same
25 canonical candidates:

1. **Share Imbalance:** descending exact signed `I_s`;
2. **raw Deployment reference:** descending `D_s`;
3. **Miner Count reference:** descending `M_s`; and
4. **Deployment-per-Miner reference:** descending exact `D_s / M_s` under its
   governed definition.

Equal values form tie groups. Each candidate in a tie receives the arithmetic
mean of the occupied one-based rank positions. Candidate identity must never
break a measurement tie. Average ranks and rational comparisons must be exact.

Only these three directed comparisons are governed:

- Share Imbalance versus raw Deployment;
- Share Imbalance versus Miner Count; and
- Share Imbalance versus Deployment per Miner.

Previously completed reference-versus-reference comparisons are scientific
lineage and must not be recomputed or presented as new Experiment 2D results.

## 7. Characterization methodology

### 7.1 Average-rank-vector classifications

For each ordering, construct the ordered 25-element exact average-rank vector
in canonical candidate-square order. For each governed comparison, assign
every eligible decision to exactly one mutually exclusive class:

1. **Identical average-rank vectors:** the vectors are element-by-element
   equal.
2. **Tie-only change:** the vectors differ and at least one candidate pair
   changes between a tie and a strict relation, but no pair that is strict in
   both orderings reverses sign.
3. **Strict ordering change:** at least one candidate pair has nonzero
   relations in both orderings with opposite signs.

The three classes are exhaustive and must be reported independently for all
three comparisons.

### 7.2 Pairwise divergence

For each of the 300 unordered candidate pairs and each governed comparison,
record the sign of the exact value relation under both orderings. Report per
decision:

- total pairwise sign disagreements;
- strict reversals;
- Share-Imbalance-tie-to-reference-strict changes; and
- Share-Imbalance-strict-to-reference-tie changes.

The counts must reconcile deterministically with the average-rank-vector
classification.

### 7.3 Rank displacement

For every candidate and governed comparison, report the exact absolute
average-rank displacement. Per decision, report:

- total rank displacement, defined as the sum of the 25 absolute candidate
  average-rank displacements;
- mean absolute rank displacement; and
- maximum absolute rank displacement.

### 7.4 Top-k membership changes

For `k` equal to 1, 3, and 5, define Top-k membership by exact average rank
`<= k`. Report whether membership differs and the number of candidates present
only in the Share Imbalance set or only in the reference set. Ties are not
broken to force exactly `k` members.

### 7.5 Tie statistics

For all four orderings, report per decision:

- tie-group count;
- number and sizes of non-singleton tie groups;
- largest tie-group size; and
- number of candidates participating in a tie.

Comparison-specific tie-to-strict and strict-to-tie behavior remains separate
from these ordering-level summaries.

### 7.6 Signed measurement distributions

Report the exact empirical distribution of the 25 canonical signed Share
Imbalance values per decision and across all eligible candidate instances.
Also report per decision:

- count of negative values;
- count of zero values;
- count of positive values;
- minimum and maximum exact imbalance; and
- exact sum of all 25 imbalances.

The exact sum must reconstruct as zero for every eligible decision because
both source share distributions sum to one. Any nonzero sum invalidates the
measurement or its arithmetic.

### 7.7 Exact empirical frequency distributions

Across the complete eligible population, report an exact empirical frequency
distribution for every classification and every per-decision scalar required
by Sections 7.2 through 7.6. Each distribution contains exact value, count,
and proportion, ordered by exact value in canonical ascending numeric order.

Binning, histograms, interpolation, quantile estimation, floating-point
aggregation, post-hoc category merging, and outcome-conditioned distributions
are prohibited.

### 7.8 Descriptive board reporting

For outcome-blind context only, comparison classes and magnitude measures may
be tabulated against:

- total deployed lamports `S_D`;
- summed per-square Miner Count memberships `S_M`;
- protocol-published `round.total_miners`, reported separately;
- count of positive-Deployment squares;
- count of positive-Miner-Count squares;
- positive per-square Miner Count range;
- Share Imbalance sign counts; and
- tie-group count and largest tie-group size for each governed ordering.

Tables must use exact empirical frequencies in deterministic canonical order.
Correlation with outcomes, regression, superiority testing, causal
explanation, and post-hoc stratum selection are prohibited.

## 8. Outcome-blind controls and required artifacts

### 8.1 Controls

Experiment 2D must execute under `outcome_blind_characterization_v1` and reuse
the Research Execution Specification v2 outcome-blind lifecycle:

- one frozen decision snapshot supplies all inputs and references;
- chronology and canonical decision ordering are immutable;
- protocol revision is homogeneous validation provenance and is not a
  measurement or ordering input;
- the runner receives no outcome source, outcome authorization, label
  provider, evaluation callback, or equivalent capability;
- no outcome-bearing or outcome-dependent artifact is declared or produced;
- population eligibility and exclusions are frozen before characterization;
- measurement, vector, reference, Replay, provenance, artifact, and manifest
  identities reconstruct fail closed;
- signed-rational arithmetic and every zero-sum invariant reconstruct exactly;
- all generated artifacts use canonical encoding;
- repeated execution from identical inputs regenerates byte-for-byte identical
  artifacts; and
- eligible and excluded dispositions reconcile exactly to the Replay
  population.

Opening or parsing an outcome source, joining a label, using outcome
availability as eligibility, performing baseline comparison, computing MRR,
executing Strategy, or producing predictive evaluation invalidates the
experiment.

### 8.2 Required artifacts

A conformant execution must produce immutable and reconstructable artifacts
for:

- source dataset and derived Replay identity;
- frozen outcome-blind provenance;
- complete eligible and excluded decision manifest with dispositions;
- the Share Imbalance definition and identity;
- the fundamental measurement and executable-binding identities;
- identities of all four governed orderings;
- per-decision signed Share Imbalance values and zero-sum validation;
- per-decision canonical average-rank vectors for all four orderings;
- per-comparison ordering classes and pairwise-divergence records;
- per-comparison rank-displacement and Top-k membership-change records;
- tie statistics for all four orderings;
- aggregate exact empirical frequency distributions;
- predeclared descriptive board reports;
- deterministic-regeneration and conformance reports; and
- one sealed outcome-blind Experiment Audit Manifest with disposition
  `outcome_access = prohibited_and_not_performed`.

No artifact may contain a winning square, label, outcome identity, outcome
availability indicator, outcome provenance, realized MRR, baseline result,
predictive metric, Strategy result, or economic result.

## 9. Interpretation

Interpretation is restricted to the three ordering comparisons. For each one,
the valid characterization must state:

- whether any average-rank-vector difference occurred;
- whether differences were absent, tie-only, strict, or a mixture;
- how frequently each class occurred; and
- the exact magnitude and distribution of divergence, displacement, Top-k
  membership changes, and ties.

The word **materially** refers only to the documented extent of ordering
change across these predeclared descriptive measures. This protocol sets no
numeric scientific-relevance threshold, continuation gate, predictive success
criterion, or authorization condition.

For each reference, the experiment may conclude only one of:

1. Share Imbalance ordering is identical throughout the eligible population;
2. Share Imbalance differs only through tie structure;
3. Share Imbalance contains strict ordering changes; or
4. the characterization is invalid because a required control, population,
   arithmetic, identity, artifact, or reconstruction requirement failed.

Conclusions must be stated separately for raw Deployment, Miner Count, and
Deployment per Miner. One comparison cannot substitute for another. No result
may be interpreted as winning-square information or predictive performance.

## 10. Completion criteria

Experiment 2D is complete only when:

- execution is valid under Research Execution Specification v2 and
  `outcome_blind_characterization_v1`;
- population accounting is complete;
- every eligible decision has 25 reconstructable canonical signed Share
  Imbalance values whose exact sum is zero;
- every eligible decision is assigned exactly one classification for each of
  the three governed comparisons;
- every required exact distribution and descriptive report is present;
- all identities and artifacts reconstruct deterministically;
- repeated generation from identical inputs is byte-for-byte identical;
- outcome access is recorded as prohibited and not performed; and
- interpretation remains limited to ordering characterization.

Completion does not authorize predictive evaluation, another experiment,
Feature Set construction, Strategy use, or economic interpretation.
