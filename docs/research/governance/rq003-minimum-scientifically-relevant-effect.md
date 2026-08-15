# RQ-003 Minimum Scientifically Relevant Effect (`Δmin`)

## Status

- Type: Research governance policy
- State: Proposed for review
- Implementation authorized: No
- Numeric `Δmin` authorized: No

This document defines the repository-wide governance policy for selecting a
minimum scientifically relevant effect under RQ-003. It does not select a
numeric threshold, revise an experiment protocol, authorize predictive
evaluation, or interpret an experiment result.

## Authority

This policy is governed by:

- [RQ-003](../questions/RQ-003-winning-square-predictability.md);
- [Finding 001](../findings/rq003-experiment-001-analysis.md);
- [Experiment 2A](../experiments/rq003-experiment-002a-deployment-per-miner-characterization.md);
- [RFC-010](../../rfcs/RFC-010-STRATEGY-LAB.md); and
- [RFC-014](../../../rfcs/RFC-014-PROTOCOL-REVISION-PROVENANCE.md).

RQ-003 governs the scientific question and explicitly requires a reviewed
analysis protocol to fix numeric effect and decision thresholds before
held-out outcome evaluation. RFC-010 preserves the separation of decision
quality from capital allocation and economic valuation. RFC-014 makes protocol
revision immutable validation provenance and prohibits its use as a ranking
signal.

## 1. Purpose

Characterization can prove that two ranking procedures are not identical, but
non-equivalence alone does not establish that the difference is large enough
to warrant an outcome-bearing predictive experiment. Conversely, statistical
power or a large sample can make a scientifically negligible difference look
precise.

`Δmin` supplies the missing relevance criterion. It prevents a continuation
decision from depending on an arbitrary count, an observed favorable result,
or statistical significance alone.

This policy separates three questions:

1. **Possibility:** can the candidate procedure produce a different ranking?
2. **Potential relevance:** could those differences support an effect at least
   as large as `Δmin`?
3. **Observed predictive evidence:** does a subsequent outcome-bearing
   experiment actually demonstrate that effect under its controls?

Characterization answers the first two without outcomes. Predictive evaluation
alone may answer the third.

## 2. Definition of `Δmin`

For an RQ-003 experiment, `Δmin` is the smallest positive improvement in the
experiment's predeclared primary decision-quality estimand that research
governance judges scientifically sufficient to justify conducting and
interpreting an outcome-bearing predictive comparison.

It is a relevance threshold, not an observed result. It is fixed before the
characterization used to apply its decision gate and before any held-out
outcome is accessed.

For a candidate procedure `C`, comparator `B`, primary metric functional `T`,
and governed evaluation population `P`, the target effect is:

```text
Δ(C, B; T, P) = T(C, P) - T(B, P)
```

`Δmin` defines the smallest positive value of that exact contrast that is
scientifically relevant for the declared research question. A change to the
candidate, comparator, metric, direction, population, decision boundary, or
protocol-revision scope creates a different estimand and requires a distinct
threshold decision.

For Experiment 2A's continuation question:

- `C` is descending Deployment-per-Miner ordering;
- `B` is descending raw-deployment ordering;
- `T` is mean reciprocal rank;
- `P` is the prospectively governed Experiment 2A decision population; and
- the direction is candidate minus comparator.

The theoretical maximum achievable MRR improvement computed by Experiment 2A
is an outcome-blind upper bound on `Δ`. It is not `Δmin`, an estimate of `Δ`,
or evidence that the bound will be achieved.

## 3. Scientific interpretation

For RQ-003, `Δmin` represents a minimum improvement in the primary ranking-
quality estimand. Where MRR is the primary metric, it is denominated in mean
reciprocal-rank units.

It does not represent:

- a standardized statistical effect size detached from the primary metric;
- a p-value, confidence level, uncertainty width, or power target;
- operational convenience or implementation cost;
- capital deployment significance;
- SOL or ORE return;
- practical mining profitability; or
- economic significance under RFC-011.

Those concepts may inform separate reviewed decisions, but they cannot be
silently substituted for RQ-003 decision-quality relevance. In particular,
RFC-010 separates ranking quality from allocation, and economic significance
requires deployment and settlement assumptions outside RQ-003.

## 4. Scope of a threshold

The governance policy is universal across RQ-003 characterization experiments;
the numeric threshold is not.

A numeric `Δmin` shall be:

- **experiment-specific**, because each experiment declares its candidate,
  comparator, primary metric, population, and scientific question; and
- **primary-contrast-specific**, because different comparators define
  different scientific increments.

It shall not be universal across all metrics or experiments. A fixed MRR
increment cannot govern a Top-k rate, calibration loss, or another estimand
without an explicit scientific mapping.

It is not measurement-family-specific: a measurement family supplies inputs,
not the evaluated contrast. The same measurement may support different
procedures and questions.

It is not Strategy-specific: RQ-003 evaluates decision-time information before
Strategy admission. A later Strategy question requires its own reviewed
governance and cannot retroactively define RQ-003 relevance.

For experiments with multiple required comparators, the protocol must identify
which contrast governs a characterization gate. It may specify separate
thresholds only when each is independently justified. A threshold vector must
not be collapsed into an undeclared aggregate.

## 5. Threshold-selection requirements

A numeric `Δmin` is justified only when a prospective governance record
provides all of the following:

1. the exact candidate procedure and comparator;
2. the primary metric, units, direction, and mathematical range;
3. the governed population, decision boundary, and protocol-revision scope;
4. a scientific reason why effects below the threshold would not justify the
   proposed predictive evaluation;
5. the evidence used to establish that reason;
6. a demonstration that the threshold was not selected from the
   characterization it will govern or from held-out outcomes;
7. sensitivity of the continuation decision to plausible alternative
   thresholds;
8. the relationship between relevance and statistical detectability;
9. an immutable threshold identity and approval record; and
10. explicit binding by the dependent experiment protocol before execution.

The numeric value must be strictly positive and expressed exactly in the
primary metric's native units. For 25-candidate MRR, protocol geometry supplies
the mathematical range but does not identify a scientifically meaningful
point inside that range.

### 5.1 Statistical justification

Statistical analysis may determine whether a proposed effect can be estimated
with adequate precision for an anticipated population. It may inform sample
requirements and whether a planned experiment is feasible.

Statistical significance, power, historical variance, and confidence-interval
width do not by themselves define scientific relevance. A threshold selected
only because the available sample can detect it is not justified.

### 5.2 Practical and operational justification

A practical rationale is admissible only when it is stated as a property of
the RQ-003 ranking question and mapped prospectively to the primary metric. For
example, an independently justified minimum change in candidate rank would
require an explicit, reviewed mapping to MRR before it could govern an MRR
contrast.

Implementation effort, runtime, or operator convenience may determine whether
research is affordable, but they do not define a scientific effect.

### 5.3 Protocol justification

Protocol structure establishes the 25-candidate rank space, valid tie
semantics, and the attainable MRR range. It can rule out impossible thresholds
and make an effect interpretable in protocol terms.

Protocol structure alone does not determine how much MRR improvement is worth
investigating. Candidate count is therefore a boundary condition, not a
numeric relevance justification.

### 5.4 Economic justification

Economic significance is outside RQ-003. It depends on deployment, inclusion,
fees, settlement, and capital assumptions owned by RFC-011 and related
economic protocols. An economic threshold must not be imported into RQ-003
without a separately approved cross-layer research question.

### 5.5 Governance justification

Governance must approve the scientific rationale and its immutable binding,
not merely the numeric literal. Approval must precede the characterization
whose result will be compared with the threshold.

A threshold may not be changed after observing the governed characterization
or predictive result. A changed threshold defines a new prospective protocol
revision; it cannot reinterpret an existing execution.

## 6. Use of existing evidence

Finding 001 establishes that direct descending deployed-lamport ordering had
MRR `0.1519459804`, with paired differences of `-0.0035856995` against the
deterministic baseline and `-0.0055509287` against the seeded-random baseline.
Its adjusted intervals crossed zero, and its fold directions were unstable.

These results establish empirical scale and uncertainty for that completed
comparison. They do not establish the smallest scientifically relevant
increment for Deployment per Miner over raw deployment. Selecting `Δmin` to
match Finding 001's point estimates, interval widths, or convenient detectable
effect would confuse prior observed variability with scientific relevance.

Finding 001 may be cited prospectively in a feasibility or sample-size review.
Because it used the same retained historical population that informs the
current research program, any threshold rationale derived from it must be
declared as development evidence and cannot make that population an
independent confirmation set.

## 7. When no justified `Δmin` exists

Absence of a justified threshold has three consequences:

1. **Characterization continues descriptively.** An outcome-blind experiment
   may measure rank-vector equivalence, tie changes, strict changes, magnitude
   distributions, and the theoretical maximum potential effect.
2. **The continuation gate remains unresolved.** The characterization must
   record `research-governance decision required`; it must not substitute a
   count, observed quantile, sample-dependent cutoff, or post hoc judgment.
3. **Predictive evaluation does not begin.** The dependent outcome-bearing
   experiment remains unauthorized until a separate prospective governance
   review approves and binds `Δmin`.

The descriptive characterization is scientifically useful even when the gate
cannot be decided. It establishes whether the procedures differ, quantifies
the attainable effect bound, and supplies evidence for a later governance
decision without opening outcomes.

## 8. Relationship to Experiment 2A

Experiment 2A should proceed with descriptive characterization only. It need
not wait for a numeric `Δmin` to generate its outcome-blind rank-vector and
potential-effect artifacts.

Without a prospectively approved `Δmin`, Experiment 2A cannot issue a passing
continuation disposition. Its result remains a characterization finding, and
Experiment 2B remains unauthorized.

After Experiment 2A completes, its observed potential-effect bound may inform
a future governance review, but it cannot be used to choose a threshold and
then retroactively pass the completed execution. A newly approved threshold
must govern a prospective protocol revision or a prospectively authorized
application whose source and threshold identities are frozen before the
decision is made.

## 9. Required governance artifact

Every approved numeric `Δmin` shall have an immutable governance artifact that
records:

- policy version;
- governed research question and experiment revision;
- candidate and comparator identities;
- primary metric, units, direction, and range;
- population and protocol-revision scope;
- exact numeric threshold and canonical representation;
- scientific rationale and evidence identities;
- feasibility analysis, if any;
- sensitivity analysis;
- approval status and approval identity; and
- creation time and prospective effective boundary.

Characterization and predictive protocols consume this artifact by identity.
They do not redefine its meaning or silently supply defaults. Missing,
ambiguous, mismatched, retrospectively created, or non-reconstructable
threshold provenance fails closed.

## 10. Policy invariants

- `Δmin` is positive and prospective.
- `Δmin` is expressed in the primary estimand's native units.
- Scientific relevance and statistical detectability remain distinct.
- Decision quality remains separate from deployment and economics.
- Protocol revision remains provenance, never a threshold input or ranking
  signal.
- Characterization remains outcome-blind.
- A potential-effect upper bound is not an observed predictive effect.
- Passing a characterization gate authorizes evaluation only; it does not
  constitute predictive evidence.
- Failure to meet `Δmin` is preserved and cannot trigger post hoc threshold
  revision.
- Missing threshold authority fails closed for predictive continuation but
  does not invalidate descriptive characterization.

## 11. Current governance determination

The repository does not currently contain evidence that identifies a
scientifically justified numeric `Δmin` for Deployment per Miner versus raw
deployment in MRR units. RQ-003 deliberately declined to derive one from
descriptive discovery, and Finding 001 does not answer that relevance
question.

The reusable policy is now defined, but the experiment-specific numeric value
is not. Selecting that value requires a separate prospective research-
governance decision supported by an independent scientific rationale.

## Recommendation

**Experiment 2A should remain descriptive until `Δmin` is established.**
