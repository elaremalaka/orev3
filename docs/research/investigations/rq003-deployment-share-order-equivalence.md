# RQ-003 Theoretical Result — Deployment Share Preserves Direct Deployment Ordering

## Status

**Type:** Theoretical research result

**Domain:** Research

**Implementation authorized:** No

This document records an algebraic equivalence proof. It is not an empirical
experiment, experiment design, implementation plan, feature authorization,
ranking authorization, or Strategy proposal.

## Authority

This result is governed by:

- [RQ-003 — Decision-Time Winning-Square Information](../questions/RQ-003-winning-square-predictability.md);
- the [Phase 3 Feature Design Review](rq003-phase3-design-review.md);
- the [RQ-003 Measurement Catalog](rq003-measurement-catalog.md);
- the [Fundamental Measurement Library design](rq003-feature-set-1-design.md);
- the Experiment 0 generator in
  [`rq003_experiment0.py`](../../../src/orev3/datasets/rq003_experiment0.py);
- [Experiment 0B](../notebook/experiment-000-characterization.md);
- [RFC-010 — Deterministic Strategy Laboratory](../../rfcs/RFC-010-STRATEGY-LAB.md); and
- [RFC-014 — Protocol Revision Provenance](../../../rfcs/RFC-014-PROTOCOL-REVISION-PROVENANCE.md).

## 1. Result

For one frozen decision observation, normalizing every candidate's deployed
lamports by the same contemporaneous positive board total preserves the exact
candidate weak ordering and every tie.

When the contemporaneous board total is zero, nonnegative deployment values
require every candidate deployment to be zero. Under the declared zero-total
Share rule, raw deployment and Deployment Share then produce the same complete
tie.

Therefore, under any direct monotone ranking by the candidate value:

- raw deployed lamports and Deployment Share produce identical descending
  rankings;
- they produce identical ascending rankings;
- they produce identical tie partitions;
- the finalized winning square receives the same rank under both
  representations; and
- every rank-based evaluation result is identical.

This conclusion is determined before outcomes are observed. Outcome data
cannot confirm, reject, strengthen, or weaken the equivalence.

## 2. Definitions

Let the ordered deployed-lamport vector from one immutable frozen normal
observation be:

`X = (x_0, x_1, ..., x_24)`

Each `x_i` is the exact nonnegative protocol-published
`round.deployed_lamports[i]` value for candidate square `i`.

Define the contemporaneous board total:

`T = sum(x_j for j in 0..24)`

For `T > 0`, define Deployment Share for square `i` as:

`s_i = x_i / T`

For `T = 0`, define all 25 Share values as zero. This rule introduces no
candidate preference and preserves the complete raw tie.

Deployment Share is dimensionless. It is not:

- lamports or SOL;
- capital allocation;
- probability or confidence;
- expected reward;
- economic value; or
- a prediction.

The board total is only the common denominator needed to define Share. This
result does not approve a separate board-total measurement or feature.

## 3. Algebraic proof

### 3.1 Positive-total case

Assume `T > 0`. For any two candidate squares `a` and `b`:

`s_a - s_b = (x_a / T) - (x_b / T)`

and therefore:

`s_a - s_b = (x_a - x_b) / T`

Because `T` is positive, division by `T` cannot change the sign of
`x_a - x_b`. It follows that:

- `x_a < x_b` if and only if `s_a < s_b`;
- `x_a > x_b` if and only if `s_a > s_b`; and
- `x_a = x_b` if and only if `s_a = s_b`.

Every pairwise comparison and equality relation is preserved. The complete
weak ordering and every tie group are therefore identical.

### 3.2 Zero-total case

Assume `T = 0`. Every `x_i` is nonnegative and their sum is zero. Consequently:

`x_0 = x_1 = ... = x_24 = 0`

The raw deployment vector is one complete tie. The declared zero-total Share
rule gives:

`s_0 = s_1 = ... = s_24 = 0`

The Share vector is the same complete tie. Raw and Share ordering therefore
remain identical.

### 3.3 Complete input domain

The fundamental deployed-lamport contract admits only nonnegative values.
Thus `T` is either positive or zero, and Sections 3.1 and 3.2 cover every valid
input under the declared semantics.

## 4. Corollaries

### 4.1 Direct ranking equivalence

Any direct ranking that is strictly monotone in the candidate value produces
the same result from `x_i` and `s_i`. This includes both ascending and
descending direct orderings.

### 4.2 Tie equivalence

Any tie rule that operates on equality groups receives exactly the same groups
from raw and Share values. Average ranks, complete ties, partial ties, and
tie-group sizes are unchanged.

### 4.3 Rank-metric equivalence

Because the winning square would occupy the same rank under both
representations, the following are necessarily identical on every common
round population:

- reciprocal rank and mean reciprocal rank;
- mean winning-square rank;
- top-1, top-3, and top-5 hit rates; and
- complete winning-square rank distributions.

No bootstrap, significance test, confirmation dataset, or additional outcome
sample is needed to establish this identity.

### 4.4 Information relationship

Deployment Share is a deterministic function of the complete raw deployment
vector. It cannot contain information absent from that vector. It discards the
absolute total scale because any positive scalar multiple of a deployment
vector produces the same Share vector.

This statement concerns the complete raw vector. A future comparison involving
a restricted raw scalar, a different information set, or a different ranking
procedure would need to define its own estimand precisely.

## 5. Assumptions

The result depends on all of the following:

1. The board contains the same canonical 25 candidate squares in both
   representations.
2. Every `x_i` is the exact protocol-published nonnegative value from one
   frozen decision observation.
3. `T` includes all and only those same 25 values.
4. Every candidate is divided by the same denominator.
5. Arithmetic preserves exact ordering and equality; approximation may not
   create, remove, or reorder ties.
6. A zero-total board maps every Share value to zero.
7. Ranking is directly monotone in the single candidate value.
8. No supplementary state, outcome, revision signal, history, candidate
   identity, or tie-break signal changes the ranking.

If any assumption changes, the altered procedure is outside this proof and
requires separate review. Violating an assumption during a purported direct
raw-versus-share comparison is nonconformance, not empirical counterevidence.

## 6. Decision-time and revision boundaries

The proof assumes that all 25 deployed-lamport inputs come from the same
immutable pre-outcome decision boundary. It does not authorize:

- a later or finalized deployment vector;
- RFC-012 evidence or historical enrichment;
- cross-observation or cross-round totals;
- missing-value repair from another observation;
- capital or settlement values from RFC-011; or
- any outcome-conditioned denominator.

RFC-014 protocol revision and activation identities remain validation and
population-control metadata. They never enter `T`, `s_i`, candidate ordering,
or tie-breaking. A revision whose deployment semantics differ requires its own
semantic eligibility decision, but that revision control does not alter the
algebra for an eligible homogeneous observation.

## 7. Empirical implications

### 7.1 No independent direct-ranking experiment

Deployment Share does not define an independent empirical experiment under the
current direct monotone ranking protocol. A Share-versus-raw execution could
test implementation conformance, canonical arithmetic, or identity handling,
but it could not test an unknown scientific proposition.

Any nonidentical raw and Share ranking would reveal an arithmetic, precision,
input-boundary, tie, or implementation defect. It would not support a Share
alternative hypothesis.

### 7.2 Separate unknown question

Whether the common deployment ordering ranks the finalized winner better than
uninformed baselines remains empirically unknown. That is a question about
direct deployed-lamport ordering, not evidence that Share contains more
information than raw deployment.

That question belongs to a separately designed empirical experiment.

## 8. Limits and future applicability

This result does not establish that Deployment Share is universally useless.
It establishes only that Share cannot change a direct monotone candidate
ordering relative to raw deployed lamports from the same board.

A future procedure could distinguish the representations if it is sensitive
to magnitude rather than only within-board order. Examples of procedurally
different questions include:

- cross-round comparisons on an explicitly governed scale;
- a nonlinear mapping of candidate magnitude;
- a learned procedure using earlier outcome-revealed rounds; or
- an interaction with separately approved contemporaneous measurements.

Those possibilities are not approved here. Each would require a separate
research question or experiment design that fixes its information set,
procedure, chronology, controls, and interpretation before outcome evaluation.
No future procedure may describe Share as containing information absent from
the complete raw vector.

The result also does not determine whether direct deployment ordering is
predictive, useful to a Strategy, economically valuable, or stable across
protocol revisions.

## 9. Role in the research workflow

This artifact is a pre-experiment feasibility result. It:

- closes Deployment Share as an independent direct-ranking Experiment 1;
- prevents redundant outcome evaluation of two necessarily identical
  rankings;
- preserves the exact assumptions and limits of the proof;
- provides a conformance oracle for any later Deployment Share implementation;
  and
- redirects the first empirical experiment toward a proposition whose outcome
  is not already fixed by algebra.

It grants no authority to implement Deployment Share, Feature Sets, ranking,
evaluation, Strategy behavior, or RFC-011 economics.

## 10. Conclusion

Deployment Share preserves direct deployed-lamport candidate ordering and ties
over the complete valid input domain. Under the current direct monotone ranking
protocol, no empirical uncertainty remains in the Share-versus-raw comparison.
The former Experiment 1 is therefore reclassified as this theoretical result.
