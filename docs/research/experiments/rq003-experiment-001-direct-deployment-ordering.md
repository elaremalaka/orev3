# RQ-003 Experiment 1 — Direct Deployment Ordering

## Status

- Research design only.
- Implementation authorized: No.
- Empirical execution authorized: No.
- Experiment protocol revision: 3 (execution-specification binding).
- Execution specification: [`rq003-research-execution-specification-v1`](../specifications/rq003-research-execution-specification.md).
- Execution specification SHA-256:
  `3f7da6977f3a4f7c31766c856fc9cc000ed6a6a0d4dffcbf6e5cd0193d948eb2`.

The first Experiment 1 execution remains invalid. This revision does not
reinterpret that execution, supply missing evidence retroactively, or
authorize a rerun.

This document is the governing protocol for the first empirical experiment
under [RQ-003](../questions/RQ-003-winning-square-predictability.md). It fixes
the scientific question, population, ranking procedures, controls, metrics,
and interpretation rules before outcomes are used for evaluation.

## 1. Scientific motivation

The protocol publishes the lamports deployed to each of the 25 candidate
squares before a round is finalized. Those values provide an atomic,
decision-time measurement of participant deployment state. It is unknown
whether directly ordering candidates by that measurement places the eventual
winning square ahead of uninformed orderings.

The [Deployment Share equivalence result](../investigations/rq003-deployment-share-order-equivalence.md)
proves that within-round share normalization preserves the ordering of raw
deployed lamports under direct monotone ranking. That proof does not establish
whether the common ordering has information about the future winner. This
experiment therefore evaluates the raw measurement directly and does not
introduce Deployment Share.

The purpose is to test for decision-time information, not to maximize
predictive performance, infer causation, or create a mining strategy.

## 2. Research question

Does direct descending ordering of candidate squares by frozen,
protocol-published deployed lamports rank the eventual winning square better
than the permanent deterministic and seeded-random uninformed baselines?

## 3. Null hypothesis

Direct descending deployed-lamport ordering does not improve winner ranking
relative to both uninformed baselines on the same eligible replay rounds. In
particular, at least one paired difference in Mean Reciprocal Rank is less
than or equal to zero, or the evidence is insufficient to establish a
positive difference.

## 4. Alternative hypothesis

Direct descending deployed-lamport ordering produces a positive, reproducible
paired improvement in Mean Reciprocal Rank over both uninformed baselines on
the same eligible replay rounds, subject to all predeclared controls and later
confirmation on a disjoint chronological interval.

The alternative does not claim that deployed lamports are probabilities,
that deployments cause the winning square, or that the ordering is
economically useful.

## 5. Required measurements

The experiment requires only the canonical fundamental measurement:

- `deployed_lamports`: the exact non-negative integer published at
  `round.deployed_lamports[candidate_square]` in the frozen decision-time
  observation.

The measurement must be produced through the existing RQ-003 immutable
execution context, executable binding, deterministic measurement pipeline,
and `MeasurementVector`. Its registered metadata and all semantic,
definition, implementation, dependency, eligibility, and binding identities
must reconstruct successfully before use.

No outcome, lifecycle-finalization field, protocol-revision value, candidate
identity, observation timing field, or other measurement may be included as
a measured input.

## 6. Required Feature Set

The experiment-specific Feature Set contains exactly one scalar:

| Position | Field | Source | Transformation |
| ---: | --- | --- | --- |
| 1 | `deployed_lamports` | Canonical fundamental measurement | None |

The Feature Set preserves the measurement value unchanged. It performs no
normalization, division, aggregation, historical reconstruction, imputation,
or outcome-dependent operation. Its schema and identity must be immutable and
recorded with the experiment.

This Feature Set is local to this experiment. It does not expand the
Measurement Library or authorize any additional Feature Set.

## 7. Required baselines

Both permanent RQ-003 uninformed baselines must rank the same 25 candidates on
exactly the same eligible decisions as the experimental procedure.

### 7.1 Deterministic baseline

The deterministic baseline orders candidates by the canonical ascending
square identifier. It consumes no measurement value or outcome. Its procedure
and identity must be fixed before evaluation.

This baseline deliberately represents a stable uninformed ordering. Its
square identifiers are structural ordering keys, not predictive inputs.

### 7.2 Seeded-random baseline

The seeded-random baseline produces one reproducible permutation per decision.
For each candidate it computes a SHA-256 digest from the canonical encoding of:

- the domain separator `rq003-experiment-001-seeded-random-v1`;
- the immutable decision identity; and
- the canonical candidate square identifier.

Candidates are ordered by ascending digest. A digest collision fails closed.
The domain separator, canonical encoding version, and procedure identity must
be recorded. No outcome, measurement value, protocol revision, timestamp, or
runtime randomness may affect the permutation.

The seeded-random baseline is a reproducible uninformed control, not a source
of repeated Monte Carlo draws.

## 8. Ranking procedure

### 8.1 Primary ordering

For every decision, candidates are ordered directly by descending
`deployed_lamports`. No scaling, learned parameter, secondary key, or
candidate-specific adjustment is permitted. A larger value means only an
earlier position in this predeclared ordering; it is not interpreted as a
probability or confidence score.

### 8.2 Tie handling

Exact equal deployed-lamport values form a tie group. Every member receives
the arithmetic mean of the one-based positions occupied by that group. For
example, three candidates tied across positions 2, 3, and 4 each receive
winner rank 3.

Candidate identity must not break measurement ties. For Top-k evaluation, a
tied winning square is a hit exactly when its average rank is less than or
equal to `k`. Tie frequency, group size, and winner-tie membership are
reported so this convention remains visible.

The deterministic and seeded-random baselines produce strict orderings and
therefore integer ranks unless their specified identity construction fails.

### 8.3 Predeclared sensitivity

An ascending deployed-lamport ordering is evaluated as a secondary,
predeclared sensitivity analysis using the same average-rank rule. It asks
whether the sign convention obscures an inverse ordering relationship. It is
not an alternative primary procedure and cannot rescue a failed primary
result, satisfy the success criteria, or be selected after inspecting
outcomes.

## 9. Evaluation protocol

### 9.1 Source and decision boundary

The initial bounded evaluation uses the archived RFC-012 research snapshot
characterized by
[Experiment 0B](../notebook/experiment-000-characterization.md). The exact
source dataset SHA-256 is
`7680856bc6a01f9b69be0921d6e66b3f43d5241a38e63b37871b6925c1d59ba7`.
The execution shall bind this experiment and its declared inputs through the
pinned RQ-003 Research Execution Specification. A byte-different dataset is a
different population and cannot be substituted silently.

There is one decision per replay round: the latest valid observation at or
before `end_slot - 5`, matching Experiment 0. If no such observation exists,
the round is excluded with reason `no_predeclared_decision_observation`.
Changing the decision offset or selection rule requires a new experiment
protocol.

#### 9.1.1 Experiment-specific execution bindings

For this experiment, the specification binds:

- Experiment 1 protocol revision `3`;
- the exact source dataset SHA-256 declared above;
- the homogeneous RFC-014 protocol-revision population admitted by Section
  9.2;
- the decision-selection rule `latest valid observation at or before
  end_slot - 5`, offset `5`, with no wider tolerance;
- canonical replay-round order by ascending immutable round chronology with
  `round_id` as the deterministic tie-breaker;
- canonical candidate order `0` through `24` within each replay round;
- the exact measurement, Feature Set, baseline, ranking, sensitivity,
  outcome-join, fold, metric, and uncertainty declarations in this protocol;
  and
- all experiment-specific artifacts listed below.

The shared specification owns source commit provenance, Replay identity,
canonical encoding, audit-manifest lifecycle, artifact contracts, population
accounting, identity continuity, reconstruction, and execution-conformance
failure semantics. This protocol does not redefine them.

### 9.2 Primary evaluation population

A round enters the primary population only when all of the following hold:

1. its replay lifecycle is classified complete;
2. its selected decision observation and fundamental measurement pass all
   identity, schema, and conformance validation;
3. it belongs to the single supported RFC-014 protocol-revision population;
4. it has exactly one valid finalized winning-square label; and
5. that label is attached only after all experimental and baseline rankings
   have been frozen.

Rounds with missing outcomes are excluded from outcome metrics and reported
as unavailable; they are never counted as misses or assigned labels. Conflicts,
ambiguous identities, mixed unsupported revisions, or malformed outcomes fail
closed.

The archived snapshot may support the initial bounded evaluation, but it is
not an independent confirmation population because it informed the governing
research program. Confirmation requires a later, chronologically disjoint
interval whose bounds and dataset identity are frozen before its outcomes are
examined.

### 9.3 Outcome-blind execution boundary

The required sequence is:

```text
Replay decision state
  -> frozen RQ003ExecutionContext
  -> fundamental MeasurementVectors
  -> one-scalar experiment Feature Set
  -> frozen primary and baseline rankings
  -> immutable outcome-blind ranking artifact
  -> finalized outcome join
  -> evaluation
```

The outcome-blind ranking artifact contains the experiment's decision and
candidate identities, measurement and Feature Set identities, procedure
identities, and ordered ranks. Its freeze, artifact binding, outcome join, and
identity continuity shall conform to the pinned execution specification. It
contains no label or outcome field.

No Strategy, DeploymentModel, Evaluator implementation from RFC-010, or
RFC-011 economic component participates in this scientific evaluation.

### 9.4 Chronological reporting

Primary eligible rounds are sorted by immutable round chronology and divided
into five consecutive folds with counts differing by at most one. There is no
random row-level or round-level split. The full initial interval is evaluated
once, and every metric is also reported for each fold in chronological order.

No parameters are fitted. The folds measure temporal consistency; they are
not training folds and must not be pooled selectively.

For this protocol, a fold or control stratum has adequate labeled support when
it contains at least 100 primary-eligible rounds. Smaller groups are reported
descriptively, but no success or failure condition depends on their direction.

### 9.5 Paired comparison

The experimental ordering and both baselines are evaluated on an identical,
round-paired population. Each comparison uses the within-round difference in
reciprocal winner rank. Any procedure-specific omission invalidates that
paired comparison.

## 10. Controls

### 10.1 Outcome-leakage control

- Freeze the decision observation, measurement vectors, Feature Set, and all
  rankings before outcome attachment.
- Reject finalized fields, outcome provenance, winning square, `won`, final
  board state, post-transition evidence, enrichment data, and any value
  reconstructed from them as inputs.
- Verify mechanically that the outcome-blind artifact schema has no outcome
  field and that its identity is unchanged after label attachment.

### 10.2 Chronology control

- Preserve round chronology throughout selection, reporting, resampling, and
  confirmation.
- Keep all 25 candidates from a round together.
- Prohibit random row-level splits and future-round history.
- Require the independent confirmation interval to begin after the initial
  interval ends.

### 10.3 Protocol-revision control

- Treat RFC-014 revision identity as immutable provenance and a population
  eligibility check only.
- Do not expose revision identity to the Feature Set or ranking procedures.
- Evaluate only one semantically supported, homogeneous revision population
  in the primary result.
- Report other revision populations separately only under a separately
  approved compatibility declaration; never pool them silently.

### 10.4 Observation-density and decision-distance controls

Neither lifecycle observation density nor decision distance may become a
ranking input. They are separate population diagnostics and cannot replace
the primary result.

#### 10.4.1 Observation-count distribution

For a replay round, `observation_count` is the number of ordered normal replay
observations in its reconstructed lifecycle before outcome attachment. RFC-012
post-transition evidence, finalized-outcome records, and enrichment records
are not observations for this count.

Report an integer frequency map from `observation_count` to round count for:

1. every replay round bound by Replay identity;
2. every outcome-blind eligible round in the ranking artifact;
3. the primary labeled evaluation population;
4. eligible rounds excluded only because their outcome is missing; and
5. rounds excluded before ranking, grouped by exclusion reason.

Each distribution must sum exactly to its corresponding population count.
This control describes lifecycle density and coverage. It is required to make
selection and outcome-availability differences associated with observation
density visible; it does not describe how close the selected observation was
to the decision boundary.

#### 10.4.2 Decision-distance cadence

For this experiment, the term `capture cadence` means only decision-distance
cadence. For an eligible decision it is the non-negative integer:

```text
decision_distance_slots = (end_slot - 5) - selected_observation_slot
```

Report counts in the predeclared strata `0`, `1`, `2`, and `3+` slots for the
complete outcome-blind ranking population and the primary labeled evaluation
population. Report the primary metrics by the same strata when support is
adequate under Section 9.4.

Inter-observation wall-clock spacing, RPC polling frequency, and collector
session sampling frequency are not `capture cadence` under this protocol and
are not required. Capture mode is separate provenance governed by Section
10.6. These requirements assess sensitivity to the temporal distance of the
selected decision snapshot and cannot replace the primary result.

### 10.5 Lifecycle control

The primary result uses only complete replay lifecycles. Incomplete-start,
incomplete-end, and incomplete-both rounds are excluded with counts and
reasons. A separately labeled sensitivity analysis may evaluate otherwise
valid incomplete lifecycles, but it cannot satisfy the success criteria.

### 10.6 Outcome availability and capture-mode control

Report eligible decision counts before the outcome join, observed labels,
enriched labels, missing labels, and all exclusions. Within the primary
population, report paired results separately for `current_round`,
`post_transition_predecessor`, and enriched outcome provenance when sample
sizes permit. Outcome source and capture mode are controls only and must not
enter ranking.

### 10.7 Evaluation-bias control

- Predeclare the primary procedure, baselines, metrics, tie rule, folds,
  uncertainty method, thresholds, and exclusions in this document.
- Evaluate all three procedures on the same rounds.
- Report every required metric and sensitivity, including unfavorable results.
- Do not tune ordering, `k`, decision timing, strata, baseline seed, or
  uncertainty settings after outcomes are observed.
- Do not interpret the ascending sensitivity or a favorable subgroup as the
  primary result.

## 11. Metrics

### 11.1 Primary metric

Mean Reciprocal Rank (MRR) is the primary metric:

```text
MRR = (1 / N) * sum(1 / winner_rank_r)
```

where `winner_rank_r` is the one-based, average-tie rank of the finalized
winning square for eligible round `r`. Report MRR for the descending ordering,
the deterministic baseline, and the seeded-random baseline, plus both paired
MRR differences.

### 11.2 Secondary metrics

Report, without replacing the primary endpoint:

- winner rank for every eligible round;
- mean and median winner rank;
- the full winner-rank distribution;
- Top-1, Top-3, and Top-5 hit rates;
- exact-tie frequency;
- number and size distribution of tie groups per round;
- winning-square tie frequency and winning tie-group size;
- all metrics by chronological fold;
- predeclared cadence, provenance, and lifecycle sensitivities; and
- ascending-order sensitivity metrics.

### 11.3 Bootstrap uncertainty

Uncertainty for the primary comparisons uses a deterministic moving-block
bootstrap over the chronologically ordered, round-level reciprocal-rank
differences:

- 10,000 bootstrap replicates;
- circular consecutive blocks;
- block length `ceil(N^(1/3))`;
- seed domain `rq003-experiment-001-moving-block-bootstrap-v1`;
- canonical SHA-256 counter expansion for deterministic block starts; and
- two-sided percentile intervals.

Because the primary claim requires superiority to two baselines, report 97.5%
intervals for each paired difference, providing a Bonferroni-controlled family
wise error rate of 0.05. Record the bootstrap procedure identity, eligible
round order, block length, seed domain, and replicate count. If the population
is too small to form the declared blocks or reconstruction differs, the
experiment is invalid rather than silently switching methods.

## 12. Interpretation rules

### Positive evidence

Positive evidence requires every success criterion in Section 13. It supports
only the bounded statement that direct descending deployed-lamport ordering
contains reproducible decision-time winner-ranking information in the tested
protocol-revision populations. It does not establish causality, profitability,
calibration, or Strategy superiority.

### Negative evidence

A valid result that fails any statistical superiority requirement is negative
evidence for the predeclared alternative. Superiority to only one baseline,
an ascending-only result, or a favorable secondary metric does not overturn
that conclusion.

### Inconclusive evidence

A result is inconclusive when the experiment executes validly but outcome
coverage, chronological confirmation, fold stability, or a required control
population is insufficient to support either a robust positive interpretation
or a useful bounded negative interpretation. Inconclusive results must be
preserved and must not trigger post hoc changes to this protocol.

## 13. Success criteria

The experiment supports the alternative hypothesis only if all of the
following are true:

1. the descending ordering has higher MRR than both baselines on the identical
   primary population;
2. the lower bound of each adjusted 97.5% paired bootstrap interval is greater
   than zero;
3. the paired MRR difference has the same positive direction in every
   chronological fold with adequate labeled support;
4. the result is not confined to one decision-distance, outcome-provenance, or
   capture-mode stratum when those strata have adequate support;
5. the complete pipeline and every artifact identity regenerate exactly;
6. all leakage, revision, chronology, cadence, lifecycle, and evaluation-bias
   controls pass; and
7. the direction and both adjusted interval conclusions reproduce on a
   predeclared, chronologically later, disjoint confirmation interval.

No secondary metric or sensitivity analysis may substitute for these criteria.

## 14. Failure criteria

The null hypothesis is not rejected when the experiment is valid but any of
the following holds:

- descending MRR is not higher than either baseline;
- either adjusted paired interval includes or falls below zero;
- superiority appears only for one baseline;
- chronological folds do not preserve the positive direction where support
  is adequate;
- evidence appears only in a sensitivity, subgroup, or ascending ordering;
- an initial positive result does not reproduce in the disjoint confirmation
  interval; or
- the result is otherwise valid but does not satisfy every success criterion.

Failure to reject the null is not proof that no decision-time information
exists under every possible procedure. It applies to this measurement,
decision boundary, direct ordering, population, and protocol revision.

## 15. Invalid experiment criteria

The experiment is invalid, and no scientific conclusion may be drawn, if any
of the following occurs:

- outcome or post-decision information enters measurement, Feature Set,
  ranking, tie handling, exclusion, or baseline construction;
- decision snapshots or ranking artifacts are not frozen before outcome join;
- protocol revision, observation cadence, lifecycle status, capture mode,
  decision identity, or candidate identity is used as a ranking signal;
- different procedures are evaluated on different round populations;
- missing or ambiguous outcomes are imputed, fabricated, or counted as misses;
- unsupported or semantically incompatible revisions are pooled;
- candidates from one round are separated by a row-level split;
- candidate identity breaks deployed-lamport ties;
- the primary direction, baseline construction, seed domain, tie rule,
  decision boundary, metric, uncertainty method, threshold, fold definition,
  or exclusion rule changes after outcomes are inspected;
- a favorable secondary, subgroup, or sensitivity result is substituted for
  the primary result;
- execution is nonconformant under the pinned RQ-003 Research Execution
  Specification;
- a required observation-count or decision-distance distribution is absent,
  uses a different definition, or does not reconcile with its population;
- Strategy, Deployment, Evaluation, or RFC-011 economics behavior is inserted
  into the experimental ranking path.

Invalidity requires correction under a newly versioned protocol before the
experiment is rerun. Results from an invalid run must not be combined with a
valid run.

## Required research artifacts

In addition to the shared artifacts required by the pinned execution
specification, an eventual authorized execution must produce these
experiment-specific artifacts:

- the selected replay population and decision-selection report;
- measurement definitions, executable bindings, and MeasurementVectors;
- the one-scalar Feature Set;
- the primary, ascending-sensitivity, and baseline procedures;
- the outcome-blind ranking artifact;
- the outcome join and provenance manifest;
- chronological folds and all exclusion reasons;
- the observation-count and decision-distance distributions;
- the bootstrap procedure and ordered resampling inputs; and
- the complete metric output.

The shared specification governs their encoding, identities, dependency
continuity, counts, hashes, reconstruction, and audit-manifest inclusion.
These declarations do not authorize implementation or execution.

## Instrumentation backlog relationship

The pinned execution specification makes its audit manifest, Replay identity,
artifact, reconstruction, and population-accounting requirements mandatory
for every future execution governed by this protocol revision. Sections
10.4.1 and 10.4.2 separately make the Experiment 1 observation-count and
decision-distance reports mandatory scientific controls.

These requirements are prospective. They do not retroactively change the
status of the earlier invalid execution.

The broader decision-to-raw-observation provenance index, artifact-only
`MeasurementVector` verification, generation-time versus artifact-time
identity documentation, deployed-lamport outlier tracing, revision-scoped
constant monitoring, and general replay-distance monitoring remain
non-blocking items in the
[RQ-003 Instrumentation Backlog](../backlog/rq003-instrumentation-backlog.md).
They are not silently incorporated into this protocol and their absence does
not invalidate a future execution.

## Scope boundary

This protocol defines one empirical comparison. It introduces no new
fundamental or derived measurement, no model, no reusable Feature Set, no
Strategy logic, no deployment behavior, and no economic analysis. Any later
use of the result in Strategy Lab or RFC-011 requires separate downstream
work governed by the corresponding architecture.
