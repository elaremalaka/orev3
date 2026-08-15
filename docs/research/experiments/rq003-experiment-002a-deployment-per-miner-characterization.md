# RQ-003 Experiment 2A — Deployment-per-Miner Ordering Characterization

## Status

- Research design only.
- Implementation authorized: No.
- Empirical execution authorized: No.
- Outcome access authorized: No.

This document governs an outcome-blind characterization of Deployment per
Miner. It does not evaluate winning-square prediction and cannot produce a
predictive finding.

## Authority

This protocol is governed by:

- [RQ-003](../questions/RQ-003-winning-square-predictability.md);
- [RFC-010](../../rfcs/RFC-010-STRATEGY-LAB.md);
- [RFC-014](../../../rfcs/RFC-014-PROTOCOL-REVISION-PROVENANCE.md);
- the [RQ-003 minimum scientifically relevant effect governance policy](../governance/rq003-minimum-scientifically-relevant-effect.md);
- the [RQ-003 Measurement Catalog](../investigations/rq003-measurement-catalog.md);
- the RQ-003 Fundamental Measurement Library;
- [Experiment 0B](../notebook/experiment-000-characterization.md); and
- [Finding 001](../findings/rq003-experiment-001-analysis.md).

The reusable artifact, identity, population-accounting, and reconstruction
mechanics are governed by the
[RQ-003 Research Execution Specification v2](../specifications/rq003-research-execution-specification-v2.md).
Its pinned SHA-256 is
`75597ab27d2d2867c68be886785c1884db83b9a26c0428c337ff23d218ef9497`.
The experiment binds execution profile
`outcome_blind_characterization_v1`. This protocol adds no outcome-bearing
artifact to those mechanics.

## 1. Purpose

Experiment 2A determines how Deployment per Miner changes the ordering already
induced by raw deployed lamports. It characterizes the derived measurement as
an observable mathematical transformation of frozen decision-time state.

It does not ask whether either ordering ranks the eventual winning square
well. Outcomes, labels, realized or outcome-joined Mean Reciprocal Rank,
predictive baselines, and superiority tests are prohibited. The outcome-blind
theoretical MRR bound required by Section 9 is not a predictive evaluation.

## 2. Characterization question

Across eligible frozen replay decisions, how often and by how much does direct
descending Deployment-per-Miner ordering differ from direct descending raw
deployed-lamport ordering?

The characterization also asks whether observed differences are strict
reversals, tie changes, or no change, and how those differences are distributed
across predeclared outcome-blind board characteristics.

## 3. Required fundamental measurements

The protocol uses exactly two existing, canonical fundamental measurements
from the same frozen `RQ003ExecutionContext`:

- `deployed_lamports[s]`: the protocol-published lamports deployed to square
  `s`; and
- `miner_count[s]`: the protocol-published miner count for square `s`.

Both values must reconstruct through their approved metadata, identities,
executable bindings, and `MeasurementVector`. No new fundamental measurement
is authorized.

## 4. Derived measurement definition

For candidate square `s`, let `D_s` be deployed lamports and `M_s` be miner
count in the same frozen decision-time observation. Deployment per Miner is
the exact rational quantity:

```text
P_s = D_s / M_s
```

subject to these exhaustive rules:

- when `M_s > 0`, represent `P_s` as the reduced non-negative rational
  `D_s / M_s`;
- when `D_s = 0` and `M_s = 0`, use the canonical empty-square extension
  `0 / 1`; and
- when `D_s > 0` and `M_s = 0`, the decision is invalid and processing fails
  closed.

Comparisons use exact integer cross multiplication. Floating-point division,
rounding, normalization, imputation, supplementary reads, historical repair,
and outcome-derived replacement are prohibited. The unit is lamports per
protocol-published miner membership.

The derived measurement uses only contemporaneous decision-time information.
It does not assert per-wallet capital, unique participant identity, causation,
or economic value.

## 5. Mathematical non-equivalence

Deployment per Miner is not generally a monotone transformation of deployed
lamports because its denominator varies by candidate. For example:

| Candidate | Deployed lamports | Miner count | Deployment per Miner |
| --- | ---: | ---: | ---: |
| A | 100 | 10 | 10 |
| B | 90 | 1 | 90 |

Raw deployment orders A before B, while Deployment per Miner orders B before
A. Therefore different strict candidate orderings are mathematically possible.
This proof establishes feasibility only; Experiment 2A measures whether and
how often such differences occur in the frozen replay population.

## 6. Population and decision boundary

The source is the immutable replay dataset used by Experiment 0 and Finding
001. Its artifact and Replay identities must be recorded under the shared
execution specification. A byte-different replay source is a different
population and cannot be substituted silently.

The protocol pins these immutable execution bindings:

- replay dataset version `replay-dataset-v1`;
- replay dataset SHA-256
  `7680856bc6a01f9b69be0921d6e66b3f43d5241a38e63b37871b6925c1d59ba7`;
- Replay identity
  `e2de7374318bff7d2644b9394106f2ddbf938e9cf8bf4133b3bb5bfe304fe31b`;
- governing protocol revision identity
  `3112ab78a64f92892a70d5d4cbd17e1d14b1c2fe`;
- execution-specification revision
  `rq003-research-execution-specification-v1` with the SHA-256 pinned above;
- canonical replay-round order by ascending immutable round chronology, with
  `round_id` as the deterministic tie-breaker; and
- canonical candidate order `0` through `24` within each replay round.

There is one decision per replay round: the latest valid observation at or
before `end_slot - 5`. A decision is eligible only when:

1. the replay lifecycle is complete;
2. the frozen decision observation is valid;
3. both required fundamental measurements reconstruct and conform;
4. the governing protocol revision is supported and homogeneous within the
   characterized population; and
5. every candidate satisfies the derived-measurement rules in Section 4.

Outcome presence, absence, value, provenance, or capture mode must not affect
eligibility. The characterization population is defined before and without an
outcome join.

## 7. Ordering procedures

For each eligible decision, construct two orderings over the same 25 canonical
candidate squares:

- raw ordering: descending `deployed_lamports`; and
- derived ordering: descending exact Deployment per Miner.

Exact equal values form tie groups. Each member receives the arithmetic mean
of its occupied one-based positions. Candidate identity must not break a
measurement tie.

## 8. Mutually exclusive ordering classifications

For each decision, construct the ordered 25-element average-rank vector under
each procedure. Vector equality means element-by-element exact equality in
canonical candidate-square order. Also record, for every unordered candidate
pair `{i, j}`, the sign of the raw value difference and the sign of the exact
derived-value difference. Each decision is assigned exactly one
classification:

1. **Identical average-rank vectors:** the two average-rank vectors are exactly
   equal.
2. **Tie-only change:** the average-rank vectors differ and at least one pair
   changes between a tie and a strict relation, but no pair with strict
   relations in both orderings reverses sign.
3. **Strict ordering change:** the average-rank vectors differ and at least one
   pair has nonzero signs in both orderings with opposite signs.

The classes are mutually exclusive and exhaustive. Both tie-only and strict
ordering changes can alter a candidate's reciprocal rank and therefore
contribute to the potential-effect calculation in Section 9.

## 9. Magnitude and distribution reporting

For each decision, report:

- pairwise sign disagreements out of the 300 unordered candidate pairs;
- strict reversals out of 300;
- tie-to-strict and strict-to-tie changes out of 300;
- absolute average-rank displacement for every candidate;
- mean and maximum absolute rank displacement;
- total rank displacement, defined as the sum of the 25 absolute candidate
  average-rank displacements;
- whether top-1, top-3, and top-5 membership changes, using average rank
  `<= k`; and
- raw and derived tie-group counts and sizes; and
- the number of candidates using the canonical `0 / 1` empty-square extension.

For each decision `r` and candidate `s`, let `R_raw(r,s)` and
`R_dpm(r,s)` be the respective exact average ranks. Compute the greatest
possible directional MRR improvement attributable to that decision without
accessing its outcome:

```text
U_r = max_s((1 / R_dpm(r,s)) - (1 / R_raw(r,s)))
```

Compute the theoretical maximum achievable population MRR improvement as:

```text
U = (1 / N) * sum_r(U_r)
```

where `N` is the number of eligible decisions. The maximization treats each
candidate in turn as a hypothetical winner; it does not read, infer, or join
the actual winning square. Report `U_r` exactly for every decision and report
the exact aggregate `U` together with its deterministic canonical encoding.
Identical average-rank vectors necessarily contribute zero. Tie-only and
strict ordering changes contribute according to their actual rank-vector
differences rather than their class label alone.

Across the full eligible population, report the exact empirical frequency
distribution of every classification and per-decision scalar magnitude. Each
distribution is an exact-value, count, and proportion table ordered by the
exact value in canonical ascending numeric order and serialized with canonical
encoding. Binning, interpolation, quantile estimation, and histogram
construction are prohibited.

For the canonical `0 / 1` empty-square extension, also report the total number
and proportion of candidate instances using it and the total number and
proportion of eligible decisions containing at least one such instance.

No winner identity or outcome metric may be joined to these summaries.

## 10. Descriptive board-characteristic reporting

Ordering-change classes and magnitudes may be described against only these
outcome-blind characteristics from the same frozen observation:

- total deployed lamports across squares;
- sum of per-square miner counts, labeled as miner memberships and not unique
  participants;
- protocol-published `round.total_miners`, reported separately;
- count of squares with positive deployed lamports;
- count of squares with positive miner counts;
- range of positive per-square miner counts; and
- raw deployed-lamport tie-group count and largest tie-group size.

Reporting is descriptive: use exact empirical frequency tables, ordered by
the board-characteristic value in canonical ascending numeric order and then
by the canonical ordering-change class, consistently with Section 9. Binning,
interpolation, and quantile estimation are prohibited. No outcome correlation,
regression, statistical superiority test, causal explanation, post hoc stratum
selection, or predictive interpretation is permitted.

## 11. Controls and validation

Execution is conformant only when all of the following hold:

- both inputs originate from one immutable observation boundary;
- measurement, context, binding, vector, replay, and artifact identities
  reconstruct deterministically;
- exact-rational comparisons regenerate byte-for-byte identically;
- candidate and decision ordering are canonical and stable;
- no outcome source is opened, parsed, joined, or represented in an artifact;
- protocol revision is validation provenance only and is not a measurement;
- all excluded decisions have one explicit disposition;
- the three ordering classifications account for every eligible decision
  exactly once; and
- repeated execution from identical inputs produces identical artifacts.

Malformed input, unsupported revision, identity conflict, zero-miner
inconsistency, partial output, or reconstruction failure invalidates the
characterization. Failures are not coerced into the identical-ordering class.

## 12. Continuation gate for Experiment 2B

The continuation gate shall compare the theoretical maximum achievable
population MRR improvement `U` from Section 9 with a prospectively approved
minimum potential effect-size threshold `delta_min`:

```text
proceed only if U >= delta_min
```

The threshold must express the smallest potential MRR improvement that
research governance considers sufficient to justify an outcome-bearing
predictive evaluation. For an execution that will apply the continuation
gate, `delta_min` and its governance identity must be approved and frozen
prospectively before that gate-bearing execution and before any outcome is
accessed. It cannot be selected from the characterization governed by that
execution or from Experiment 2B results.

No existing repository-governance document establishes a scientifically
justified numeric value for `delta_min`. RQ-003 explicitly leaves numeric
effect-size thresholds to a reviewed experiment protocol. Selecting
`delta_min` is therefore an unresolved future research-governance question,
not an authorized constant in this protocol.

Experiment 2A may execute descriptively without `delta_min`, characterize and
report rank-vector differences and `U`, and produce Finding 002. Such an
execution must record `research-governance decision required`; its continuation
gate cannot pass, and Experiment 2B remains unauthorized. Its observed result
cannot be used to select `delta_min` and then retroactively pass that execution.

Experiment 2B remains unauthorized until a prospectively approved `delta_min`
and governance identity exist and a gate-bearing Experiment 2A execution
satisfies `U >= delta_min`. In that execution, identical vectors, tie-only
changes, and strict ordering changes all contribute only through their exact
effect on `U`; no count threshold or class label may substitute for the
potential-effect calculation.

Passing the completed gate will authorize only the already specified
Experiment 2B question. It will not constitute predictive evidence.

## 13. Required characterization artifacts

A conformant execution must produce immutable, reconstructable artifacts for:

- source and Replay identity;
- outcome-blind audit provenance;
- eligible and excluded decision manifest with dispositions;
- derived-measurement definition and identity;
- per-decision raw and derived ordering identities;
- per-decision ordering class and magnitude values;
- aggregate class counts and distributions;
- predeclared descriptive board-characteristic reports;
- per-decision and aggregate theoretical maximum MRR improvement;
- the approved minimum potential effect-size threshold and its governance
  identity, when one exists;
- continuation-gate result or unresolved-governance disposition; and
- deterministic regeneration and conformance validation.

No artifact may contain a winning square, label, outcome provenance, outcome
availability indicator, realized or outcome-joined MRR, predictive baseline,
or evaluation result. The theoretical potential-effect bound defined in
Section 9 is required and contains no outcome information.

## 14. Finding 002

Every valid Experiment 2A execution shall produce an immutable Finding 002
that preserves at minimum:

- characterization validity;
- average-rank-vector class counts;
- pairwise divergence summaries;
- rank-displacement summaries;
- Top-k membership-change summaries;
- tie statistics;
- canonical `0 / 1` empty-square-extension frequency;
- theoretical maximum achievable population MRR improvement `U`;
- `delta_min` governance status and governance identity, when one exists; and
- continuation disposition.

Finding 002 is a descriptive characterization finding. It must not choose
`delta_min`, authorize Experiment 2B, reinterpret the characterization, add an
outcome-bearing analysis, or convert the theoretical bound into observed
predictive evidence. Authorization of Experiment 2B remains owned by the
prospectively governed continuation gate.

## 15. Interpretation and completion

Experiment 2A has one of four dispositions:

- **Minimum potential effect satisfied:** valid execution, prospectively
  approved `delta_min`, and `U >= delta_min`; Experiment 2B may proceed.
- **Minimum potential effect not satisfied:** valid execution, prospectively
  approved `delta_min`, and `U < delta_min`; Experiment 2B must not proceed.
- **Research-governance decision required:** valid characterization but no
  prospectively approved `delta_min`; Experiment 2B remains unauthorized.
- **Invalid characterization:** any required control, identity, population,
  arithmetic, artifact, or reconstruction requirement fails.

None of these dispositions is a claim about winning-square prediction.
