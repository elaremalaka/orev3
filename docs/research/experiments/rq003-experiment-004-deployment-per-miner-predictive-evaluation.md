# RQ-003 Experiment 4 — Deployment-per-Miner Predictive Evaluation

## Status

- Type: Governing research protocol
- Research design: Complete
- Implementation authorized: No
- Empirical execution authorized: No
- Research Execution Specification:
  [v2](../specifications/rq003-research-execution-specification-v2.md)
- Execution profile: `outcome_aware_v1`

This document prospectively governs the predictive evaluation of direct
Deployment-per-Miner ordering. It reuses the validated Experiment 3
predictive framework without changing its population, baselines, ranking
conventions, controls, metrics, uncertainty method, or interpretation rules.
Only the governed measurement changes.

The protocol does not authorize implementation, execution, Strategy behavior,
deployment, or economic analysis. It does not revise any repository governance
requirement or authorize work that separate governance leaves blocked.

## Authority

This protocol is governed by:

- [RQ-003 — Decision-Time Winning-Square Information](../questions/RQ-003-winning-square-predictability.md);
- [RFC-010](../../rfcs/RFC-010-STRATEGY-LAB.md);
- [RFC-014](../../../rfcs/RFC-014-PROTOCOL-REVISION-PROVENANCE.md);
- [RQ-003 Research Execution Specification v2](../specifications/rq003-research-execution-specification-v2.md);
- [Finding 002 — Deployment-per-Miner Ordering Characterization](../findings/rq003-experiment-002-analysis.md);
- [Finding 005 — Miner Count Predictive Evaluation](../findings/rq003-experiment-003-analysis.md); and
- the [RQ-003 Predictive Evaluation Roadmap](../investigations/rq003-predictive-evaluation-roadmap.md).

Where this protocol reuses predictive methodology, Experiment 3 is the
validated scientific reference. The derived measurement and its direct
ordering are the only scientific procedure changes.

## 1. Scientific motivation

Finding 002 established outcome-blindly that Deployment per Miner is not an
empirical duplicate of direct Deployment. It produced strict ordering changes
in every eligible characterization decision, with no identical or tie-only
average-rank vectors. That result establishes structural novelty, not
predictive information.

Finding 005 established negative evidence for direct descending Miner Count
under the validated Experiment 3 predictive framework. The Experiment 3
protocol also preserves Finding 001's negative evidence for direct descending
Deployment. Neither direct fundamental result answers whether the exact local
relationship between deployed lamports and miner count contains different
decision-time winner-ranking information.

Experiment 4 asks that distinct empirical question. It does not test
causality, profitability, participant identity, deployment allocation,
Strategy performance, or incremental value in a combined procedure.

## 2. Research question

Does direct descending ordering of candidate squares by exact frozen
Deployment per Miner rank the eventual winning square better than the
permanent deterministic and seeded-random uninformed baselines?

## 3. Hypotheses

### 3.1 Null hypothesis

Direct descending Deployment-per-Miner ordering does not improve winner
ranking relative to both required uninformed baselines on the same eligible
replay rounds. At least one paired Mean Reciprocal Rank difference is less than
or equal to zero, or the evidence is insufficient to establish a positive,
reproducible difference under the required controls.

### 3.2 Alternative hypothesis

Direct descending Deployment-per-Miner ordering produces a positive,
reproducible paired improvement in Mean Reciprocal Rank over both required
uninformed baselines on the same eligible replay rounds, remains directionally
consistent under the predeclared controls, and later reproduces on a disjoint
chronological confirmation interval.

The alternative does not assert that Deployment per Miner is a probability,
causes the winner, should be combined with another signal, or has economic
value.

## 4. Governed measurement

### 4.1 Inputs

The governed measurement uses exactly two approved fundamental measurements
from the same frozen `RQ003ExecutionContext`:

- `deployed_lamports[s]`: the exact non-negative integer published for
  candidate square `s`; and
- `miner_count[s]`: the exact non-negative integer published for candidate
  square `s`.

Both inputs must be produced through their immutable metadata,
definition-specific context views, executable bindings, deterministic
measurement pipeline, and immutable `MeasurementVector`. Their semantic,
definition, implementation, dependency, eligibility, and executable-binding
identities must reconstruct before derivation.

### 4.2 Exact derived measurement

For square `s`, let `D_s` be deployed lamports and `M_s` be miner count from
the same frozen decision observation. Deployment per Miner is:

```text
P_s = D_s / M_s
```

with these exhaustive rules:

- when `M_s > 0`, represent `P_s` as the canonical reduced non-negative
  rational pair `(D_s / gcd(D_s, M_s), M_s / gcd(D_s, M_s))`;
- when `D_s = 0` and `M_s = 0`, use the canonical empty-square extension
  `0 / 1`; and
- when `D_s > 0` and `M_s = 0`, the decision fails measurement conformance
  closed and cannot be ranked.

The unit is lamports per protocol-published miner membership. Rational
comparison uses exact integer cross multiplication. Floating-point division,
rounding, imputation, supplementary reads, historical repair, outcome-derived
replacement, and any additional normalization are prohibited.

The derived value is a decision-time measurement only. It does not represent
per-wallet capital, unique participants, cost, reward, probability, or
economic value. Candidate identity, protocol revision, timing, lifecycle,
capture mode, and outcome availability are not measurement inputs.

## 5. Experiment Feature Set

The experiment-local Feature Set contains exactly one scalar concept:

| Position | Field | Source | Transformation |
| ---: | --- | --- | --- |
| 1 | `deployment_per_miner` | Canonical exact derived measurement | None |

The Feature Set preserves the reduced rational pair and its immutable identity
unchanged. It contains no raw Deployment field, Miner Count field, Share
Imbalance, other derived measurement, historical input, label, or audit
variable.

This protocol neither creates a reusable Feature Set nor changes the
Fundamental Measurement Library.

## 6. Required baselines

Both permanent RQ-003 uninformed baselines rank the same 25 candidates at the
same decision point and are evaluated on exactly the same round population as
the experimental ordering.

### 6.1 Deterministic baseline

The deterministic baseline orders candidates by canonical ascending square
identifier. It consumes no measurement, outcome, chronology, or protocol
state. Its procedure identity is frozen before outcome access.

Square identifiers are structural keys for this uninformed control. They are
not inputs to Deployment-per-Miner ordering and must not break measurement
ties.

### 6.2 Seeded-random baseline

The seeded-random baseline produces one reproducible uninformed permutation
per decision using deterministic SHA-256 ordering over canonical decision and
candidate identities under domain separator
`rq003-experiment-004-seeded-random-v1`. A digest collision fails closed.

The baseline receives no measurement, outcome, outcome provenance, protocol
revision, timestamp, dataset location, or runtime randomness. Its domain
separator, canonical encoding, procedure identity, and seed binding must be
frozen before outcome access. A favorable seed may not be selected after
evaluation.

### 6.3 Baseline parity

The experimental procedure and both baselines must share:

- the identical ranked-decision population;
- the identical labeled evaluation population;
- the same decision points and candidate set;
- the same winner-rank, Top-k, fold, and uncertainty definitions; and
- the same outcome source and provenance rules.

Any procedure-specific omission invalidates the affected comparison.

## 7. Ranking procedure

### 7.1 Primary ordering

For each frozen decision, order all 25 candidates directly by descending exact
`deployment_per_miner`. No secondary key, learned parameter, scaling,
candidate-specific adjustment, or other measurement is permitted.

A larger exact rational means only an earlier position in this governed
ordering. It is not interpreted as probability, confidence, value, or
deployment advice.

### 7.2 Average-rank tie handling

Candidates with exactly equal reduced rational values form a tie group. Every
candidate in the group receives the arithmetic mean of the one-based positions
occupied by that group. Candidate identity must not break measurement ties.
For Top-k reporting, a winning candidate is a hit exactly when its average
rank is less than or equal to `k`.

### 7.3 Predeclared ascending sensitivity

Evaluate ascending Deployment per Miner as a secondary sensitivity using the
same exact comparison and average-rank convention. It is not a second primary
procedure and cannot rescue a failed descending result, satisfy a success
criterion, or be selected after outcomes are observed.

## 8. Execution and evaluation protocol

### 8.1 Immutable bindings

Before implementation or execution authorization, freeze and record:

- this protocol's revision and content identity;
- the source commit;
- Research Execution Specification revision `v2`;
- execution profile `outcome_aware_v1`;
- experiment configuration identity;
- source dataset persisted-byte and logical-content identities;
- the derived Replay identity;
- the homogeneous supported RFC-014 protocol-revision identity;
- both fundamental-measurement identities;
- the Deployment-per-Miner semantic, definition, implementation, dependency,
  eligibility, and executable-binding identities;
- Feature Set, ranking, baseline, sensitivity, metric, uncertainty, and
  artifact identities; and
- every experiment-specific artifact declaration in Section 15.

Replay identity is reconstructed from its first-order bindings and ordered
Replay population under the execution specification. It is not embedded as a
historical literal. The protocol document and source state must be committed
before an official execution can bind them.

### 8.2 Initial dataset and decision point

The bounded initial evaluation uses the immutable cumulative RFC-012 research
snapshot:

- dataset version: `replay-dataset-v1`;
- dataset SHA-256:
  `7680856bc6a01f9b69be0921d6e66b3f43d5241a38e63b37871b6925c1d59ba7`;
- Replay rounds: 18,653;
- complete lifecycles: 17,912;
- locally observed outcomes: 3,507; and
- missing outcomes: 15,146.

One decision is selected per Replay round: the latest valid normal observation
at or before `end_slot - 5`. If none exists, exclude the round before ranking
with disposition `no_predeclared_decision_observation`. A decision whose
Deployment-per-Miner value is undefined under Section 4.2 is excluded before
ranking with one explicit conformance disposition. Do not substitute a
different observation or repair a value using outcome knowledge.

Replay rounds are ordered by ascending immutable chronology with `round_id` as
the deterministic tie-breaker. Candidates are ordered canonically from square
`0` through square `24` before a ranking procedure assigns ranks.

Changing the dataset, decision offset, decision-selection rule, chronology,
candidate population, or derived-measurement definition requires a new
protocol revision.

### 8.3 Outcome-blind freeze and outcome boundary

Execution follows this sequence:

```text
Replay decision state
  -> frozen DecisionContext
  -> immutable RQ003ExecutionContext
  -> fundamental MeasurementVector
  -> exact Deployment-per-Miner measurement
  -> one-scalar Experiment 4 Feature Set
  -> primary, sensitivity, and baseline rankings
  -> frozen outcome-blind ranking artifact
  -> authorized outcome join
  -> evaluation
```

Before outcome access, validate and freeze the outcome-blind provenance block,
population dispositions, fundamental and derived identities, Feature Set
identity, every ranking record, artifact declarations, and ranking artifact.
The ranking artifact contains no label, winner, outcome availability, capture
mode, or outcome provenance.

Only after the frozen ranking reconstructs may the `outcome_aware_v1` profile
authorize the declared outcome source and join valid labels. No outcome may
alter snapshot selection, exclusions, measurement values, ties, or ranks.

### 8.4 Evaluation population

A round enters the primary evaluation population only when:

1. its Replay lifecycle is complete;
2. the predeclared decision, both fundamental measurements, and the exact
   derived measurement pass schema, identity, and conformance validation;
3. it belongs to the single supported homogeneous protocol-revision
   population;
4. all three primary procedures produced ranks on the same 25 candidates; and
5. exactly one valid finalized winning-square label is joined after ranking
   freeze.

Missing outcomes remain missing and are excluded from outcome metrics. They
are not imputed, inferred, or counted as misses. Incomplete lifecycles are
excluded from the primary endpoint and may appear only in the separately
labeled lifecycle sensitivity.

The archive supports a bounded initial evaluation, not independent temporal
confirmation. Support for the alternative requires a later, immutable,
chronologically disjoint confirmation interval that was not used to select
the procedure or interpretation.

### 8.5 Chronological folds and adequate support

Sort primary eligible rounds by immutable chronology and divide them into five
consecutive folds whose counts differ by at most one. No parameter is fitted;
the folds assess temporal consistency. Random row-level, observation-level, or
round-level splitting is prohibited.

A fold or control stratum has adequate labeled support when it contains at
least 100 primary-eligible rounds. Smaller groups are reported descriptively,
but their direction does not determine success or failure.

### 8.6 Paired evaluation

Evaluate descending Deployment per Miner and both baselines on the identical
primary population. Pair reciprocal-rank differences by round. Preserve the
round as the independent unit in every aggregate and uncertainty calculation.

## 9. Controls

### 9.1 Outcome and future-information control

- Freeze normal snapshots and `DecisionContext` before any RFC-012 evidence
  consumption.
- Permit only the two frozen fundamental measurements and their exact
  Deployment-per-Miner derivation as experimental inputs.
- Exclude winners, finalized fields, future observations, outcome
  availability, capture mode, RFC-012 evidence, enrichment, and replay
  internals from measurement and ranking.
- Freeze all rankings before outcome authorization.
- Verify that outcome attachment does not change any ranking identity.

Any violation invalidates the experiment.

### 9.2 Chronology control

- Preserve ascending round chronology in selection, folds, resampling, and
  reporting.
- Keep all 25 candidates from a round together.
- Prohibit later-round state or labels from influencing an earlier ranking.
- Require any confirmation interval to begin after the initial interval.

### 9.3 Protocol-revision control

Protocol revision is immutable provenance and validation information only. It
must not enter the Feature Set, derived arithmetic, tie handling, or ranking.
The primary population must be semantically homogeneous under the supported
RFC-014 revision binding. Unsupported or incompatible revisions are reported
separately and never silently pooled.

### 9.4 Observation-count and decision-distance controls

For each governed population, report the exact empirical frequency map from
normal Replay `observation_count` to round count. At minimum report it for:

1. all Replay-bound rounds;
2. all ranked decisions;
3. the primary labeled evaluation population;
4. ranked rounds excluded only for a missing outcome; and
5. pre-ranking exclusions grouped by reason.

Each map must reconcile exactly with its population. RFC-012 evidence and
outcome records are not normal observations.

For each ranked decision define:

```text
decision_distance_slots = (end_slot - 5) - selected_observation_slot
```

Report the predeclared strata `0`, `1`, `2`, and `3+` slots for the full
ranked population and the primary labeled population. Report primary metrics
within each adequately supported stratum. Decision distance, observation
count, wall-clock spacing, and collector cadence remain audit variables and
must not enter ranking.

### 9.5 Lifecycle control

Use only complete Replay lifecycles for the primary result. Report
partial-start, partial-end, and partial-both counts separately. Otherwise
valid incomplete lifecycles with labels may be evaluated only as a predeclared
sensitivity and cannot satisfy success criteria.

### 9.6 Outcome availability and provenance control

Report ranked decisions, available valid outcomes, missing outcomes, observed
outcomes, enriched outcomes, and every exclusion. Within the primary
population, report paired metrics separately for `current_round`,
`post_transition_predecessor`, and enriched provenance where support is
adequate.

Outcome source, capture mode, and enrichment status are evaluation provenance
only. They must not affect eligibility before the join or enter ranking.

### 9.7 Evaluation-bias control

- Freeze the primary direction, exact arithmetic, zero rules, tie rule,
  decision point, baselines, baseline seed domain, folds, metrics, uncertainty
  method, support threshold, and exclusions before outcome access.
- Evaluate all primary procedures on identical populations.
- Report every required endpoint and sensitivity, including unfavorable
  results.
- Do not tune arithmetic, tie handling, direction, decision timing, strata,
  seed, uncertainty, or interpretation after outcomes are observed.
- Do not use ascending Deployment per Miner, a favorable subgroup, or a
  secondary endpoint to rescue the primary result.

## 10. Metrics

### 10.1 Primary endpoint

Mean Reciprocal Rank is the primary endpoint:

```text
MRR = (1 / N) * sum(1 / winner_rank_r)
```

`winner_rank_r` is the finalized winning square's one-based average rank in
round `r`. Report MRR for descending Deployment per Miner, deterministic
baseline, and seeded-random baseline, plus both paired MRR differences.

MRR is a ranking-quality measure. It is not a probability, reward, deployment,
or economic metric.

### 10.2 Secondary endpoints

Report without replacing the primary endpoint:

- the winner rank for every primary round;
- mean and median winner rank;
- the complete winner-rank distribution;
- Top-1, Top-3, and Top-5 hit rates;
- exact-tie frequency;
- tie-group count and size distributions;
- winning-square tie frequency and winning tie-group size;
- all metrics by chronological fold;
- decision-distance, lifecycle, and outcome-provenance sensitivities; and
- ascending Deployment-per-Miner sensitivity metrics.

## 11. Uncertainty

Use the Experiment 3 deterministic circular moving-block bootstrap on the
chronologically ordered, round-paired reciprocal-rank differences:

- 10,000 replicates;
- circular consecutive blocks;
- block length `ceil(N^(1/3))`;
- seed domain `rq003-experiment-004-moving-block-bootstrap-v1`;
- canonical SHA-256 counter expansion for deterministic block starts; and
- two-sided percentile intervals.

Because the primary claim requires superiority to two baselines, report a
97.5% interval for each paired difference, providing Bonferroni control of the
family-wise error rate at 0.05. Freeze and record the bootstrap identity,
ordered eligible rounds, block length, seed domain, and replicate count before
outcome access.

If the population cannot support the declared construction, or deterministic
reconstruction differs, do not substitute another method. Apply the invalidity
or insufficiency rule in Sections 14 and 13.3 as appropriate.

## 12. Scientific interpretation

### 12.1 Positive evidence

Positive evidence requires every success criterion in Section 13.1. It
supports only the bounded statement that direct descending Deployment per
Miner contains reproducible decision-time winner-ranking information under
the tested population, decision boundary, and protocol revision.

It does not establish causality, profitability, calibration, incremental
value over another participant-state signal, or Strategy suitability.

### 12.2 Negative evidence

A valid result that fails a required statistical-superiority condition is
negative evidence for the predeclared alternative. Superiority to only one
baseline, an ascending-only result, or a favorable secondary metric does not
overturn that conclusion.

### 12.3 Inconclusive evidence

A valid result is inconclusive when outcome coverage, chronological support,
control-population support, or independent confirmation is insufficient to
support either a robust positive interpretation or a useful bounded negative
interpretation. Record the exact unresolved requirement. Do not alter the
protocol after seeing results.

### 12.4 Initial and confirmation dispositions

The archived dataset can produce a bounded initial result. It cannot, by
itself, satisfy RQ-003's independent-confirmation requirement because it has
already informed procedure selection. An initially favorable result remains
provisional until the same frozen procedure is evaluated on the required
disjoint later interval.

## 13. Success and failure criteria

### 13.1 Success criteria

The experiment supports the alternative hypothesis only when all of the
following hold:

1. descending Deployment-per-Miner MRR is higher than both baselines on the
   identical primary population;
2. the lower bound of each adjusted 97.5% paired bootstrap interval is greater
   than zero;
3. paired MRR differences are positive against both baselines in every
   chronological fold with adequate support;
4. the result is not confined to one decision-distance, lifecycle, or
   outcome-provenance stratum when those strata have adequate support;
5. the execution, generated artifacts, identities, and manifest reconstruct
   and regenerate deterministically;
6. every leakage, chronology, revision, cadence, lifecycle, provenance, and
   evaluation-bias control passes;
7. the same frozen procedure reproduces the direction and adjusted interval
   conclusions on a predeclared, chronologically later, disjoint confirmation
   interval; and
8. the conclusion is limited to populations supported by outcome
   availability.

No secondary endpoint or sensitivity may substitute for these requirements.

### 13.2 Failure criteria

The null is not rejected when execution is valid and any of the following is
true:

- descending Deployment-per-Miner MRR is not higher than either baseline;
- either adjusted paired interval includes or falls below zero;
- superiority appears against only one baseline;
- adequately supported chronological folds do not preserve the positive
  direction against both baselines;
- evidence appears only in an ascending sensitivity, subgroup, or secondary
  endpoint;
- an initial favorable result does not reproduce in the disjoint confirmation
  interval; or
- the result otherwise fails any success criterion while remaining valid and
  scientifically interpretable.

Failure to reject the null is bounded to this measurement, direct ordering,
decision boundary, population, and protocol revision. It does not establish
that Deployment per Miner cannot contribute under every separately governed
procedure.

### 13.3 Insufficient evidence

Evidence is insufficient when the execution is valid but inadequate eligible
outcomes, unresolved population comparability, inadequate control support, or
missing independent confirmation prevents a justified positive or bounded
negative disposition. Preserve the valid artifacts and name the unmet
criterion; do not convert insufficiency into success or failure post hoc.

## 14. Invalid experiment criteria

The experiment is invalid and provides no evidence for either hypothesis if:

- outcome or post-decision information enters either fundamental measurement,
  the derived measurement, Feature Set, tie handling, ranking, baseline, or
  pre-outcome exclusions;
- the ranking artifact is not frozen before outcome access;
- RFC-012 evidence enters Replay, `DecisionContext`, or a ranking input;
- candidate identity breaks exact Deployment-per-Miner ties;
- floating-point division, rounding, imputation, or an unapproved zero rule
  changes a derived value or ordering;
- protocol revision, observation count, decision distance, lifecycle, capture
  mode, outcome availability, decision identity, or chronology is used as a
  ranking signal;
- primary procedures use different decisions, candidates, or labeled rounds;
- missing or ambiguous outcomes are imputed, fabricated, or counted as misses;
- unsupported or semantically incompatible revisions are pooled;
- rows, observations, or candidates from a round cross temporal partitions;
- the primary direction, exact arithmetic, zero rule, tie rule, decision
  boundary, baseline construction, seed domain, folds, metric, uncertainty
  method, or exclusion rule changes after outcome access;
- a favorable sensitivity, subgroup, or secondary metric replaces the primary
  result;
- population distributions or disposition counts fail to reconcile;
- canonical identity, artifact, Replay, provenance, dependency, or manifest
  reconstruction fails;
- deterministic regeneration is not byte-identical where required;
- execution is nonconformant with Research Execution Specification v2 and
  `outcome_aware_v1`; or
- Strategy, Deployment, RFC-011 economics, or any non-research behavior enters
  the experimental path.

An invalid execution must stop without scientific interpretation. Correction
requires a prospectively versioned protocol or implementation as appropriate;
invalid and valid executions may not be combined.

## 15. Required artifacts

An authorized execution must produce every shared artifact required by
Research Execution Specification v2 for `outcome_aware_v1`, including:

- immutable experiment, specification, profile, source-commit, dataset,
  protocol-revision, and configuration bindings;
- validated external-source provenance and derived Replay identity;
- complete ordered pre-outcome population accounting;
- the frozen outcome-blind provenance block;
- one canonical outcome-blind ranking primary artifact;
- the declared outcome-source contract and authorized outcome join;
- complete post-outcome dispositions;
- canonical evaluation artifacts; and
- the sealed outcome-aware Experiment Audit Manifest.

The execution must also produce these experiment-specific artifacts:

1. decision-selection and ranked-population report;
2. fundamental-measurement metadata, identities, executable bindings, and
   `MeasurementVector` provenance;
3. Deployment-per-Miner definition, exact-rational conformance, zero-case
   accounting, and immutable identities;
4. one-scalar Feature Set schema and identity;
5. descending primary, ascending sensitivity, deterministic baseline, and
   seeded-random procedure definitions and identities;
6. candidate exact values, ranks, and tie-group records for every ranked
   decision;
7. outcome-label and capture-provenance join report;
8. exclusion and disposition report;
9. observation-count distributions;
10. decision-distance distributions and adequate-stratum report;
11. chronological-fold report;
12. lifecycle and outcome-provenance sensitivity reports;
13. complete primary and secondary metrics;
14. paired round-level comparison records;
15. bootstrap configuration, deterministic resampling identity, replicate
    output, and adjusted intervals;
16. protocol-control and future-information audit; and
17. deterministic reconstruction and regeneration report.

Every generated artifact must satisfy the specification's canonical encoding,
identity, dependency, hash, byte-count, record-count, and reconstruction
contracts. External sources retain their persisted-byte provenance and
separate canonical logical identities.

## 16. Completion boundary

Experiment 4 is complete when a conformant execution preserves all required
artifacts and records exactly one scientific disposition: positive evidence,
negative evidence, inconclusive evidence, or invalid execution.

Completion does not authorize:

- a reusable or combined Feature Set;
- predictive evaluation of Share Imbalance;
- feature or procedure tuning;
- Strategy admission or execution;
- capital deployment;
- RFC-011 economic evaluation; or
- production use.

Any downstream experiment or decision-engine work requires separate
prospective governance and authorization.
