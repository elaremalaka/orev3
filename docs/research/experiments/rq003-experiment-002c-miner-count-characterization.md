# RQ-003 Experiment 2C — Miner Count Ordering Characterization

## Status

- Research design only.
- Implementation authorized: No.
- Empirical execution authorized: No.
- Outcome access authorized: No.

This document governs an outcome-blind characterization of direct per-square
Miner Count ordering. It does not evaluate winning-square prediction and does
not authorize a predictive experiment.

## Authority

This protocol uses only:

- [RQ-003](../questions/RQ-003-winning-square-predictability.md);
- the [RQ-003 Measurement Catalog](../investigations/rq003-measurement-catalog.md);
- the [Feature Eligibility Resolution](../questions/RQ-003-feature-eligibility-resolution.md);
- the [RQ-003 Research Execution Specification v2](../specifications/rq003-research-execution-specification-v2.md);
- [Finding 001](../findings/rq003-experiment-001-analysis.md); and
- [Finding 002](../findings/rq003-experiment-002-analysis.md).

The experiment binds Research Execution Specification revision
`rq003-research-execution-specification-v2` and execution profile
`outcome_blind_characterization_v1`. The specification owns reusable
identity, provenance, population-accounting, artifact, reconstruction, and
terminal-manifest mechanics. This protocol owns only the scientific
characterization defined below.

## 1. Scientific motivation

Finding 001 reports negative evidence for direct descending deployed-lamport
ordering under its governed predictive protocol. Finding 002 establishes,
without outcomes, that Deployment per Miner materially changes candidate
ordering relative to raw Deployment. Neither finding characterizes direct
per-square Miner Count ordering.

Miner Count is an approved fundamental measurement rather than a derived
quantity. Characterizing its direct ordering completes the contemporaneous
participant-state comparator foundation needed to distinguish the information
content of Deployment, Miner Count, and their already characterized
Deployment-per-Miner relationship. The characterization is necessary before
any later governance considers further predictive evaluation of
Deployment-per-Miner relationships.

This motivation does not assert that Miner Count predicts a winner, represents
economic value, or should enter Strategy.

## 2. Research question

Across eligible frozen replay decisions, does descending direct per-square
Miner Count ordering differ from:

1. descending raw Deployment ordering; and
2. descending exact Deployment-per-Miner ordering?

For each comparison, the protocol asks whether average-rank vectors are
identical, differ only through ties, or contain strict ordering changes, and
how large the observed ordering differences are.

The experiment does not ask which ordering is better, whether any ordering
predicts the winning square, or whether any observed difference is
economically useful.

## 3. Measurement definition

### 3.1 Governed measurement

The experiment introduces no new or derived measurement. Its sole governed
measurement is the approved fundamental per-square Miner Count:

```text
M_s = round.miner_counts[s]
```

For candidate square `s`, `M_s` is the protocol-published count of distinct
Miner authorities recorded on that square in the frozen normal observation.
It is read unchanged from the immutable decision-time context. It must remain
an unsigned integer and must reconstruct through its approved metadata,
identity, executable binding, and `MeasurementVector`.

The measurement performs no arithmetic, normalization, ranking,
interpretation, historical reconstruction, supplementary read, or
cross-account repair. It does not represent people, devices, transactions, or
the protocol-published round-wide unique-authority aggregate.

### 3.2 Reference orderings

The two comparison orderings are scientific references, not new measurements:

- **Raw Deployment reference:** descending protocol-published per-square
  deployed lamports from the same frozen observation, with the direct ordering
  semantics characterized by Finding 001.
- **Deployment-per-Miner reference:** descending exact rational
  Deployment-per-Miner ordering under the definition and zero handling bound
  by the valid Finding 002 characterization.

The execution must reconstruct both reference orderings from their governed
identities and the same frozen observation boundary. It must not redefine,
extend, tune, or reinterpret either reference. The already completed raw
Deployment versus Deployment-per-Miner comparison is historical lineage and
is not a third Experiment 2C comparison.

## 4. Mathematical assessment

### 4.1 Miner Count versus Deployment

Miner Count ordering is not generally a monotonic transformation of
Deployment ordering because the two protocol-published quantities vary
independently by square. For example:

| Candidate | Deployed lamports | Miner Count |
| --- | ---: | ---: |
| A | 100 | 5 |
| B | 90 | 10 |

Descending Deployment orders A before B, while descending Miner Count orders
B before A. Strictly different orderings are therefore mathematically
possible.

### 4.2 Miner Count versus Deployment per Miner

Miner Count ordering is not generally a monotonic transformation of
Deployment-per-Miner ordering. For example:

| Candidate | Deployed lamports | Miner Count | Deployment per Miner |
| --- | ---: | ---: | ---: |
| A | 100 | 10 | 10 |
| B | 90 | 5 | 18 |

Descending Miner Count orders A before B, while descending Deployment per
Miner orders B before A. Strictly different orderings are therefore
mathematically possible.

These examples prove non-equivalence only. They do not establish that a
difference occurs in the governed replay population or that any ordering has
predictive value.

## 5. Population and immutable bindings

The experiment uses the immutable replay population characterized by Finding
002. A byte-different replay source is a different population and cannot be
substituted silently. A conformant execution must bind:

- replay dataset version `replay-dataset-v1`;
- replay dataset SHA-256
  `7680856bc6a01f9b69be0921d6e66b3f43d5241a38e63b37871b6925c1d59ba7`;
- protocol revision identity
  `3112ab78a64f92892a70d5d4cbd17e1d14b1c2fe` as validation provenance only;
- Research Execution Specification revision
  `rq003-research-execution-specification-v2`;
- execution profile `outcome_blind_characterization_v1`;
- the immutable Experiment 2C protocol and configuration identities;
- the frozen implementation source-commit provenance identity;
- the immutable decision-selection configuration identity;
- canonical replay-round order by ascending immutable round chronology, with
  `round_id` as the deterministic tie-breaker; and
- canonical candidate order `0` through `24` within each decision.

Replay identity is derived rather than embedded. It must reconstruct from the
bound execution specification, execution profile, experiment configuration,
source commit, replay dataset, decision-selection configuration, and ordered
Replay population. The reconstructed identity must be frozen in the
outcome-blind provenance and audit manifest.

There is one decision per replay round: the latest valid observation at or
before `end_slot - 5`. A decision is eligible only when:

1. the replay lifecycle is complete;
2. the frozen decision observation is valid;
3. Miner Count and both reference-ordering inputs reconstruct and conform;
4. all three orderings cover the same 25 canonical candidates;
5. the protocol revision is supported and homogeneous within the population;
   and
6. the Deployment-per-Miner reference satisfies its governed zero and exact
   rational rules.

Every excluded decision must receive exactly one deterministic pre-outcome
disposition. Outcome availability, identity, value, provenance, and capture
mode must not affect eligibility.

## 6. Ordering procedures

For every eligible decision, construct exactly three orderings over the same
25 candidates:

1. **Miner Count:** descending `M_s`;
2. **raw Deployment reference:** descending deployed lamports; and
3. **Deployment-per-Miner reference:** descending exact rational Deployment
   per Miner.

Equal values form tie groups. Each candidate in a tie receives the arithmetic
mean of the occupied one-based rank positions. Candidate identity must never
break a measurement tie. Average ranks and rational comparisons must be exact;
floating-point comparison is prohibited.

Only these two directed comparisons are governed:

- Miner Count versus raw Deployment; and
- Miner Count versus Deployment per Miner.

## 7. Characterization methodology

### 7.1 Average-rank-vector classifications

For each ordering, construct the ordered 25-element average-rank vector in
canonical candidate-square order. For each governed comparison, assign every
eligible decision to exactly one mutually exclusive class:

1. **Identical average-rank vectors:** the two vectors are element-by-element
   equal.
2. **Tie-only change:** the vectors differ and at least one candidate pair
   changes between a tie and a strict relation, but no pair that is strict in
   both orderings reverses sign.
3. **Strict ordering change:** at least one candidate pair has nonzero
   relations in both orderings with opposite signs.

The three classes must be exhaustive and independently reported for both
governed comparisons.

### 7.2 Pairwise divergence

For each of the 300 unordered candidate pairs and each governed comparison,
record the sign of the value relation under both orderings. Report per
decision:

- total pairwise sign disagreements;
- strict reversals;
- tie-to-strict changes; and
- strict-to-tie changes.

The four counts must reconcile deterministically with the average-rank-vector
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
`<= k`. Report whether membership differs between the two orderings and the
number of candidates entering and leaving each Top-k set. Ties are not broken
to force exactly `k` members.

### 7.5 Tie statistics

For all three orderings, report per decision:

- tie-group count;
- number and sizes of non-singleton tie groups;
- largest tie-group size; and
- number of candidates participating in a tie.

Report comparison-specific tie-to-strict and strict-to-tie behavior separately
as required by Section 7.2.

### 7.6 Exact empirical frequency distributions

Across the complete eligible population, report an exact empirical frequency
distribution for every classification and per-decision scalar defined in
Sections 7.2 through 7.5. Each distribution must contain exact value, count,
and proportion, ordered by exact value in canonical ascending numeric order.

Binning, histogram construction, interpolation, quantile estimation,
post-hoc category merging, and outcome-conditioned distributions are
prohibited.

## 8. Outcome-blind descriptive board reporting

For context only, the two comparison classes and magnitude measures may be
tabulated against these predeclared values from the same frozen observation:

- total deployed lamports across all squares;
- summed per-square miner memberships, explicitly distinct from unique
  miners;
- protocol-published `round.total_miners`, reported separately;
- count of squares with positive deployed lamports;
- count of squares with positive Miner Count;
- range of positive per-square Miner Count;
- Miner Count tie-group count and largest tie-group size; and
- raw Deployment and Deployment-per-Miner tie-group counts.

Reporting must use exact empirical frequency tables in deterministic canonical
order. It is descriptive only. Correlation with outcomes, regression,
superiority testing, causal explanation, and post-hoc stratum selection are
prohibited.

## 9. Controls

Experiment 2C must execute under the
`outcome_blind_characterization_v1` profile. It reuses the Research Execution
Specification v2 outcome-blind lifecycle and controls applied to Finding 002:

- one frozen decision-time observation supplies all measurement and reference
  values;
- chronology and canonical decision ordering are immutable;
- protocol revision is homogeneous validation provenance and is not an input
  to any ordering;
- the runner receives no outcome source, outcome authorization, label
  provider, evaluation callback, or equivalent capability;
- no outcome-bearing or outcome-dependent artifact is declared or produced;
- population eligibility and exclusions are fixed before characterization;
- all measurement, binding, vector, Replay, provenance, artifact, and manifest
  identities reconstruct fail closed;
- all generated artifacts use the specification's canonical encoding;
- repeated execution from identical inputs regenerates byte-for-byte identical
  artifacts; and
- all eligible and excluded decisions reconcile exactly to the Replay
  population.

Opening or parsing an outcome source, joining a label, using outcome
availability as eligibility, performing baseline comparison, computing MRR,
executing Strategy, or producing a predictive evaluation invalidates the
experiment.

## 10. Required artifacts

A conformant execution must produce immutable and reconstructable artifacts
for:

- source dataset and derived Replay identity;
- frozen outcome-blind provenance;
- complete eligible and excluded decision manifest with dispositions;
- Miner Count measurement and executable-binding identities;
- identities of both governed reference orderings;
- per-decision canonical rank vectors for all three orderings;
- per-comparison ordering class and pairwise-divergence records;
- per-comparison rank-displacement and Top-k membership-change records;
- tie statistics for all three orderings;
- aggregate exact empirical frequency distributions;
- the predeclared descriptive board reports;
- deterministic-regeneration and conformance reports; and
- one sealed outcome-blind Experiment Audit Manifest with disposition
  `outcome_access = prohibited_and_not_performed`.

No artifact may contain a winning square, label, outcome identity, outcome
availability indicator, outcome provenance, realized MRR, baseline result,
predictive metric, Strategy result, or economic result.

## 11. Interpretation

Interpretation is restricted to the two ordering comparisons. For each one,
the valid characterization must state:

- whether any average-rank-vector difference occurred;
- whether differences were absent, tie-only, strict, or a mixture;
- how frequently each class occurred; and
- the exact observed magnitude and distribution of divergence, displacement,
  Top-k membership changes, and ties.

The word **materially** refers only to the documented extent of ordering
change across these predeclared descriptive measures. This protocol does not
set a numeric scientific-relevance threshold, continuation gate, predictive
success criterion, or authorization condition. It must not convert ordering
difference into a claim about winning-square information.

The experiment may conclude only one of:

1. Miner Count ordering is identical to the reference ordering throughout the
   eligible population;
2. Miner Count ordering differs only through tie structure;
3. Miner Count ordering contains strict ordering changes; or
4. the characterization is invalid because a required control, population,
   identity, artifact, or reconstruction requirement failed.

Conclusions must be stated separately for raw Deployment and Deployment per
Miner. One comparison cannot substitute for the other.

## 12. Completion criteria

Experiment 2C is complete only when:

- the execution is valid under Research Execution Specification v2 and
  `outcome_blind_characterization_v1`;
- population accounting is complete;
- every eligible decision is assigned exactly one classification for each
  governed comparison;
- every required exact distribution and descriptive report is present;
- all identities and artifacts reconstruct deterministically;
- outcome access is recorded as prohibited and not performed; and
- the interpretation remains limited to ordering characterization.

Completion does not authorize predictive evaluation, another experiment,
Feature Set construction, Strategy use, or economic interpretation.
