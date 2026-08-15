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
- the [RQ-003 Measurement Catalog](../investigations/rq003-measurement-catalog.md);
- the RQ-003 Fundamental Measurement Library;
- [Experiment 0B](../notebook/experiment-000-characterization.md); and
- [Finding 001](../findings/rq003-experiment-001-analysis.md).

The reusable artifact, identity, population-accounting, and reconstruction
mechanics are governed by the
[RQ-003 Research Execution Specification v1](../specifications/rq003-research-execution-specification.md).
This protocol adds no outcome-bearing artifact to those mechanics.

## 1. Purpose

Experiment 2A determines how Deployment per Miner changes the ordering already
induced by raw deployed lamports. It characterizes the derived measurement as
an observable mathematical transformation of frozen decision-time state.

It does not ask whether either ordering ranks the eventual winning square
well. Outcomes, labels, Mean Reciprocal Rank, predictive baselines, and
superiority tests are prohibited.

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

For every unordered candidate pair `{i, j}`, record the sign of the raw value
difference and the sign of the exact derived-value difference. Each decision
is assigned exactly one classification:

1. **Identical ordering:** every pair has the same sign in both orderings.
2. **Tie-only change:** at least one pair changes between a tie and a strict
   relation, but no pair with strict relations in both orderings reverses sign.
3. **Strict reordering:** at least one pair has nonzero signs in both orderings
   and those signs are opposite.

The classes are mutually exclusive and exhaustive. A tie-only change is not a
strict reversal and does not satisfy the continuation gate in Section 12.

## 9. Magnitude and distribution reporting

For each decision, report:

- pairwise sign disagreements out of the 300 unordered candidate pairs;
- strict reversals out of 300;
- tie-to-strict and strict-to-tie changes out of 300;
- absolute average-rank displacement for every candidate;
- mean and maximum absolute rank displacement;
- total rank displacement;
- whether top-1, top-3, and top-5 membership changes, using average rank
  `<= k`; and
- raw and derived tie-group counts and sizes.

Across the full eligible population, report counts, proportions, exact value
distributions, and the minimum, maximum, median, and predeclared quartiles of
each magnitude. Report the complete distribution where the value domain is
small; otherwise report a deterministic histogram whose bin edges are frozen
before execution.

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

Reporting is descriptive: counts and the same deterministic distribution
summaries from Section 9. No outcome correlation, regression, statistical
superiority test, causal explanation, post hoc stratum selection, or
predictive interpretation is permitted.

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

Experiment 2B may proceed only after a valid Experiment 2A execution shows
strict reordering in at least 100 eligible decisions.

This threshold is a prospective minimum-support rule. It does not assert that
100 decisions are predictive, statistically sufficient for a positive result,
or economically meaningful. It prevents a predictive experiment whose only
difference from raw deployment is sparse or tie-only behavior.

The following do not satisfy the gate:

- identical ordering;
- tie-only changes;
- invalid decisions;
- post hoc pooling across different protocol revisions; or
- any ordering difference discovered with outcome access.

Passing the gate authorizes only the already specified Experiment 2B question.
It does not constitute predictive evidence.

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
- continuation-gate result; and
- deterministic regeneration and conformance validation.

No artifact may contain a winning square, label, outcome provenance, outcome
availability indicator, MRR, predictive baseline, or evaluation result.

## 14. Interpretation and completion

Experiment 2A has one of three dispositions:

- **Meaningful ordering differences:** valid execution and at least 100
  eligible decisions with strict reordering; Experiment 2B may proceed.
- **Insufficient strict ordering differences:** valid execution but fewer than
  100 eligible decisions with strict reordering; Experiment 2B must not
  proceed under its current protocol.
- **Invalid characterization:** any required control, identity, population,
  arithmetic, artifact, or reconstruction requirement fails.

None of these dispositions is a claim about winning-square prediction.
