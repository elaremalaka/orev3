# RQ-003 Experiment 2B — Deployment-per-Miner Ranking Evaluation

## Status

- Research design only.
- Implementation authorized: No.
- Empirical execution authorized: No.
- Conditional prerequisite: a valid
  [Experiment 2A](rq003-experiment-002a-deployment-per-miner-characterization.md)
  execution must satisfy its continuation gate.

This protocol is dormant until that prerequisite is met and its immutable
artifact identities are bound prospectively. Experiment 2A does not evaluate
outcomes; Experiment 2B is the separate predictive evaluation.

## Authority

This protocol is governed by:

- [RQ-003](../questions/RQ-003-winning-square-predictability.md);
- [RFC-010](../../rfcs/RFC-010-STRATEGY-LAB.md);
- [RFC-014](../../../rfcs/RFC-014-PROTOCOL-REVISION-PROVENANCE.md);
- the [RQ-003 Measurement Catalog](../investigations/rq003-measurement-catalog.md);
- the RQ-003 Fundamental Measurement Library;
- the completed, valid Experiment 2A characterization; and
- [Finding 001](../findings/rq003-experiment-001-analysis.md).

Reusable execution mechanics are governed by the
[RQ-003 Research Execution Specification v1](../specifications/rq003-research-execution-specification.md).
The direct raw-deployment comparator and permanent baselines follow the
scientific conventions established by
[Experiment 1](rq003-experiment-001-direct-deployment-ordering.md).

## 1. Scientific motivation

Experiment 2A can establish that normalizing deployed lamports by
protocol-published miner count produces materially different strict candidate
orderings. It cannot establish whether those differences contain information
about the eventual winning square.

Experiment 2B asks that outcome-bearing question only after the difference is
demonstrated outcome-blind. The purpose is to test decision-time information,
not to maximize performance, infer causation, or create a mining strategy.

## 2. Research question

Does direct descending Deployment-per-Miner ordering rank the eventual winning
square better than direct descending raw-deployed-lamport ordering and both
permanent uninformed baselines on the same eligible replay rounds?

## 3. Null hypothesis

Deployment-per-Miner ordering does not improve winner ranking relative to all
three comparators on the same eligible rounds. In particular, at least one
paired Mean Reciprocal Rank difference is less than or equal to zero, or the
evidence is insufficient to establish a positive difference under the
predeclared controls.

## 4. Alternative hypothesis

Deployment-per-Miner ordering produces a positive, reproducible paired
improvement in Mean Reciprocal Rank over raw deployment, the deterministic
baseline, and the seeded-random baseline, subject to every predeclared control
and later confirmation on a disjoint chronological interval.

The alternative does not assert causation, probability calibration, unique
participant economics, or practical mining value.

## 5. Required Experiment 2A binding

Before implementation or execution, this protocol must bind:

- the immutable identity of a valid Experiment 2A characterization;
- its immutable Finding 002 identity;
- its source dataset and Replay identities;
- its derived-measurement semantic and definition identities;
- its eligible and excluded population manifest identities;
- its average-rank-vector classification counts;
- its theoretical maximum achievable population MRR improvement;
- its prospectively approved minimum potential effect-size threshold and
  governance identity; and
- its successful continuation-gate disposition.

Those bindings must be frozen without outcome access. Experiment 2B may not
change the Deployment-per-Miner definition, zero-miner rules, decision point,
or population rule after inspecting Experiment 2A or outcome data.

If Experiment 2A is invalid, lacks a prospectively approved minimum potential
effect-size threshold, or does not satisfy that threshold, Experiment 2B is
unauthorized under this protocol.

## 6. Required measurements and derived measurement

The experiment uses exactly the canonical fundamental measurements:

- `deployed_lamports[s]`; and
- `miner_count[s]`.

It consumes exactly the Deployment-per-Miner definition frozen by Experiment
2A:

```text
P_s = D_s / M_s
```

with reduced exact rationals for `M_s > 0`, canonical `0 / 1` when both values
are zero, and fail-closed invalidity when `D_s > 0` and `M_s = 0`.
Comparisons use integer cross multiplication. No floating point, rounding,
imputation, normalization beyond the specified ratio, supplementary read,
historical reconstruction, or outcome-derived replacement is permitted.

## 7. Experiment Feature Set

The Experiment 2B Feature Set contains exactly one scalar concept:

| Position | Field | Source | Transformation |
| ---: | --- | --- | --- |
| 1 | `deployment_per_miner` | Experiment 2A derived measurement | None |

The Feature Set preserves the exact derived value and identity unchanged. It
does not include raw deployment as an additional input; raw deployment is a
separate comparator. No other measurement or derived measurement is admitted.

## 8. Comparators

Every procedure ranks the same 25 candidates on exactly the same eligible
decisions.

### 8.1 Raw-deployment comparator

The scientific comparator orders candidates by descending canonical
`deployed_lamports`, with average-rank tie handling. It is the primary
incremental-information comparator because Finding 001 already evaluated this
ordering and Experiment 2A measures how the derived ordering differs from it.

### 8.2 Deterministic baseline

The permanent deterministic baseline orders candidates by ascending canonical
square identifier. It consumes no measurement or outcome.

### 8.3 Seeded-random baseline

The permanent seeded-random baseline computes one deterministic SHA-256 key
per decision and candidate from:

- domain separator `rq003-experiment-002b-seeded-random-v1`;
- immutable decision identity; and
- canonical candidate square identifier.

Candidates are ordered by ascending digest. Digest collision fails closed.
The baseline consumes no measurement, outcome, protocol revision, timestamp,
or runtime randomness.

## 9. Ranking procedure

### 9.1 Primary ordering

Candidates are ordered by descending exact Deployment per Miner. No learned
parameter, secondary key, or candidate-specific adjustment is permitted.

Exact equal rational values form a tie group. Every member receives the
arithmetic mean of the occupied one-based positions. Candidate identity must
not break measurement ties. For Top-k metrics, a winner is a hit when its
average rank is `<= k`.

### 9.2 Predeclared sensitivity

Ascending Deployment-per-Miner ordering is reported as a secondary sensitivity
using the same tie rule. It cannot rescue the primary result, satisfy success
criteria, or be selected after outcome inspection.

## 10. Evaluation protocol

### 10.1 Population and decision point

The bounded initial evaluation uses the same immutable replay source,
RFC-014-supported homogeneous revision population, complete-lifecycle rule,
and decision point as Experiment 2A: the latest valid observation at or before
`end_slot - 5`.

A round enters the primary evaluation population only when:

1. it was eligible in the bound Experiment 2A manifest;
2. all input, context, measurement, derived-measurement, Feature Set, ranking,
   and artifact identities reconstruct;
3. it has exactly one valid finalized winning-square label; and
4. the label is joined only after all four rankings are frozen.

Missing outcomes are excluded from outcome metrics and reported as
unavailable. They are never counted as misses or assigned labels. Conflicts,
ambiguous identities, malformed outcomes, or unsupported revision mixtures
fail closed.

### 10.2 Outcome-blind boundary

The required sequence is:

```text
Replay decision state
  -> frozen RQ003ExecutionContext
  -> fundamental MeasurementVectors
  -> frozen Deployment-per-Miner derived measurement
  -> one-scalar Experiment 2B Feature Set
  -> frozen experimental and comparator rankings
  -> immutable outcome-blind ranking artifact
  -> finalized outcome join
  -> evaluation
```

No outcome field may enter Replay snapshots, `DecisionContext`, the execution
context, measurements, Feature Set, or ranking. No Strategy, DeploymentModel,
RFC-010 Evaluator implementation, or RFC-011 economics component participates.

### 10.3 Chronological reporting

Eligible evaluation rounds are sorted by immutable round chronology and
divided into five consecutive folds with counts differing by at most one. All
metrics are reported for the full bounded population and each fold. Folds are
stability reports, not random splits or fitted validation sets.

The same predeclared observation-count, decision-distance, lifecycle, revision,
and outcome-provenance reporting used by Experiment 1 must be produced for the
Experiment 2B population.

## 11. Metrics

### 11.1 Primary endpoint

The primary endpoint is round-level Mean Reciprocal Rank (MRR) of the winning
square under Deployment-per-Miner ordering.

Report paired round-level MRR differences against:

1. raw deployed-lamport ordering;
2. deterministic baseline; and
3. seeded-random baseline.

The raw-deployment difference is the primary incremental-information contrast.
All three comparisons are required for positive evidence.

### 11.2 Secondary metrics

For every procedure report:

- winner-rank distribution;
- Top-1, Top-3, Top-5, and Top-10 hit rates;
- mean and median winner rank; and
- tie frequency, tie-group size, and winner-tie membership.

Also report the experimental-minus-raw winner-rank difference. Secondary
metrics describe the result and cannot override the primary endpoint.

### 11.3 Bootstrap uncertainty

Use a paired moving-block bootstrap over chronologically ordered rounds:

- 10,000 replicates;
- block length `ceil(N^(1/3))`;
- domain-separated deterministic seed
  `rq003-experiment-002b-moving-block-bootstrap-v1`; and
- simultaneous two-sided 59/60 confidence intervals for the three paired MRR
  differences, preserving family-wise alpha `0.05` by Bonferroni adjustment.

The experimental and comparator scores for a round must remain paired within
every replicate. If the population has fewer than 100 evaluable rounds, the
result is inconclusive rather than positive.

## 12. Controls

The execution must verify:

- **Outcome leakage:** rankings and their artifact are frozen before outcome
  access.
- **Chronology:** canonical chronological ordering and five consecutive folds
  are preserved.
- **Revision:** one supported homogeneous governing revision is used;
  revision is provenance and validation metadata, never a ranking input.
- **Experiment 2A continuity:** the bound definition, decision population,
  strict-reordering gate, and identities reconstruct unchanged.
- **Feature Set:** exactly one derived scalar is admitted; no post hoc feature
  addition or selection occurs.
- **Lifecycle:** primary rounds have complete lifecycles; every exclusion has
  one disposition.
- **Cadence:** observation-count and decision-distance distributions are
  reported, not used as ranking inputs.
- **Evaluation:** all four procedures use identical rounds, labels, tie rules,
  and metric implementations.
- **Identity and reconstruction:** source, Replay, audit manifest, measurement,
  derived measurement, Feature Set, ranking, outcome join, and evaluation
  artifacts reconstruct deterministically.
- **Outcome provenance:** observed and enriched outcomes are reported
  separately; missing outcomes are not fabricated.

## 13. Interpretation rules

### 13.1 Positive evidence

The experiment provides positive evidence only when all of the following hold:

- the mean paired MRR difference is positive against all three comparators;
- the simultaneous confidence interval lower bound is above zero for all
  three differences;
- all five chronological folds have positive paired MRR differences against
  all three comparators;
- the improvement is not confined to one predeclared lifecycle, cadence,
  decision-distance, or outcome-provenance stratum;
- every control and deterministic reconstruction passes; and
- a later, chronologically disjoint confirmation interval reproduces the
  direction under the frozen procedure.

The bounded initial dataset alone cannot complete the last condition.

### 13.2 Negative evidence

The experiment provides negative evidence when execution is valid and the
Deployment-per-Miner ordering fails to improve mean paired MRR over at least
one comparator, without a control failure that would instead make the result
invalid.

### 13.3 Inconclusive evidence

The experiment is inconclusive when execution is valid but uncertainty spans
zero, chronological directions are inconsistent, support is below 100 rounds,
the apparent result is confined to one predeclared control stratum, or
independent confirmation is not yet available.

Positive-looking secondary or ascending-sensitivity results cannot change an
inconclusive or negative primary disposition.

## 14. Success, failure, and invalidity criteria

### 14.1 Success criteria

Success requires every positive-evidence condition in Section 13.1. Success
means only that this predeclared decision-time ordering satisfies RQ-003's
evidence standard; it does not authorize a Strategy or economic claim.

### 14.2 Failure criteria

A valid experiment fails to support the alternative when it meets the
negative-evidence rule. Failure is a scientific result and must not trigger
post hoc modification of the ordering or population.

### 14.3 Invalid experiment criteria

The experiment is invalid if:

- Experiment 2A did not validly satisfy the continuation gate;
- a bound Experiment 2A identity or population fails continuity;
- an outcome is accessed before ranking-artifact freeze;
- the Feature Set contains any undeclared input;
- experimental and comparator procedures use different populations or labels;
- exact-rational, tie, bootstrap, or fold rules differ from this protocol;
- protocol revisions are mixed contrary to RFC-014;
- missing outcomes are fabricated or counted as misses;
- any required identity, artifact, provenance, population, or reconstruction
  check fails; or
- execution departs from the pinned shared execution specification.

An invalid execution has no scientific interpretation.

## 15. Required artifacts

A conformant execution must produce the shared execution-specification
artifacts plus experiment-specific immutable artifacts for:

- the Experiment 2A prerequisite binding and continuation-gate proof;
- fundamental and derived measurement identities;
- the one-scalar Feature Set identity;
- all four frozen ranking procedures and outcome-blind rankings;
- eligible, excluded, and outcome-unavailable populations;
- outcome join and provenance counts;
- primary and secondary metrics;
- paired bootstrap output;
- five chronological-fold reports;
- observation-count and decision-distance reports;
- lifecycle and provenance reports; and
- deterministic regeneration and protocol-conformance validation.

No scientific conclusion may be drawn unless all required artifacts validate.

## 16. Relationship to later work

Experiment 2B evaluates ranking information only. It does not create a
Strategy, prescribe deployment, estimate economic value, or modify RFC-010,
RFC-011, RFC-012, or RFC-014. Any later Strategy Lab or RFC-011 economics use
requires separate reviewed work after RQ-003 evidence standards are met.
