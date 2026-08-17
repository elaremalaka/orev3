# RQ-003 Predictive Evaluation Roadmap

## Status and scope

- Type: Research planning
- Implementation authorized: No
- Experiment protocol authorized: No
- Predictive execution authorized: No

This roadmap uses only:

- [Finding 001](../findings/rq003-experiment-001-analysis.md);
- [Finding 002](../findings/rq003-experiment-002-analysis.md);
- [Finding 003](../findings/rq003-experiment-002c-analysis.md);
- Finding 004 as reconstructed from the sealed
  [Experiment 2D execution artifacts](../../../data/research/analyses/rq003/experiment-002d-share-imbalance-characterization/first-official-b09400d/); and
- the [Participant-State Family Review](../findings/rq003-participant-state-family-review.md).

It orders future scientific evaluations of three already characterized
participant-state signals:

1. Miner Count;
2. Deployment per Miner; and
3. Signed Deployment–Miner Share Imbalance.

The roadmap does not define an experiment, protocol, Feature Set, baseline,
metric, threshold, ranking artifact, implementation phase, Strategy, or
production decision. Each future evaluation remains subject to separate
prospective scientific and governance authorization.

## 1. Scientific starting point

The participant-state family has one predictive finding and three
ordering-characterization findings:

- Direct descending Deployment produced negative evidence under Finding 001.
- Deployment per Miner differs strictly from Deployment in every eligible
  Finding 002 decision.
- Miner Count differs strictly from Deployment and Deployment per Miner in
  every eligible Finding 003 decision.
- Signed Share Imbalance differs strictly from Deployment and Miner Count in
  every eligible Finding 004 decision, but overlaps strongly with Deployment
  per Miner: 8,980 of 17,912 average-rank vectors are identical, and 8,932 are
  strictly different.

All six pairwise relationships among Deployment, Miner Count, Deployment per
Miner, and Signed Share Imbalance are therefore characterized. The dominant
unknown is no longer ordering novelty. It is whether any of the three
unevaluated orderings contains decision-time information about the eventual
winning square beyond uninformed comparison procedures.

## 2. Roadmap principles

The evaluation order follows five scientific principles.

### 2.1 Fundamental before derived

Evaluate the unevaluated fundamental ordering before relationships derived
from it. Miner Count can be interpreted without assuming that a particular
Deployment–Miner relationship is scientifically useful.

### 2.2 Structural independence before overlap

Prefer the ordering that contributes the most distinct structure. Miner Count
is highly divergent from all other core orderings, while Share Imbalance and
Deployment per Miner form a closely overlapping relationship cluster.

### 2.3 Representative relationship before incremental variant

Evaluate Deployment per Miner before Share Imbalance. Deployment per Miner is
the simpler local relationship. Its result supplies the necessary scientific
reference for deciding what, if anything, Share Imbalance's smaller ordering
differences contribute.

### 2.4 Preserve the accepted Deployment result

Finding 001 remains the established direct-Deployment predictive reference.
Future evaluations should compare new evidence with that finding without
reinterpreting or tuning the completed Deployment procedure.

### 2.5 Ordering novelty is not predictive evidence

The amount of pairwise divergence determines likely information gain from an
evaluation, not expected predictive direction. No signal receives priority
because it is presumed to perform well.

## 3. Recommended evaluation order

### 3.1 First — Miner Count

### Scientific question to resolve

Does direct Miner Count ordering contain decision-time information about the
eventual winning square beyond uninformed comparison procedures?

This statement identifies the future scientific question only. It is not a
governing protocol.

### Scientific dependencies

Miner Count depends on:

- Finding 001 as the accepted direct-Deployment predictive reference;
- Finding 003 as proof that Miner Count is not an empirical duplicate of
  Deployment or Deployment per Miner; and
- the frozen decision-time and outcome-isolation boundaries already accepted
  by RQ-003 research.

It does not depend on a predictive result for Deployment per Miner or Share
Imbalance.

### Why it is first

Miner Count is the only unevaluated fundamental participant-state ordering.
It is also the most structurally independent member of the core map:

- mean pairwise disagreement with Deployment is approximately `163.1639` of
  300 pairs;
- mean disagreement with Deployment per Miner is approximately `255.9071`;
- mean disagreement with Share Imbalance is approximately `255.9365`; and
- every eligible Miner Count ordering contains ties not reproduced by the
  other core orderings.

Evaluating Miner Count first produces the clearest test of whether the second
atomic participant-state quantity contains information absent from the
negative direct-Deployment result. It also avoids interpreting a derived
relationship before either of its two fundamental orderings has completed an
individual predictive evaluation.

### Expected information gain

**High.** Any valid result materially advances the family:

- positive evidence would identify the first supported participant-state
  ordering after Deployment's negative result;
- negative evidence would show that extensive structural independence alone
  did not translate into demonstrated predictive information; and
- inconclusive evidence would quantify the unresolved uncertainty for the
  family's tie-rich fundamental axis.

No outcome permits skipping the remaining relationship evaluations because
their orderings are empirically non-equivalent to Miner Count.

### 3.2 Second — Deployment per Miner

### Scientific question to resolve

Does exact Deployment-per-Miner ordering contain decision-time information
about the eventual winning square beyond uninformed comparison procedures and
the accepted direct-Deployment result?

This statement does not define the mechanics of a future experiment.

### Scientific dependencies

Deployment per Miner depends on:

- Finding 001 as the direct-Deployment predictive reference;
- Finding 002 as proof of material ordering novelty relative to Deployment;
- Finding 003 as proof that it is not an empirical duplicate of Miner Count;
  and
- completion of the Miner Count predictive finding for coherent comparison of
  the two principal unevaluated participant-state axes.

The measurement's scientific eligibility does not depend on Miner Count
having a positive result. The dependency is interpretive: evaluating Miner
Count first establishes whether the local ratio is being compared with two
known fundamental results rather than one known and one unknown result.

### Why it is second

Deployment per Miner is the simplest characterized relationship between
Deployment and Miner Count. It differs strictly from Deployment in all 17,912
eligible decisions, with approximately `92.7432` mean pairwise disagreements
and approximately `134.3138` mean total rank displacement.

It should precede Share Imbalance because Finding 004 shows substantial
ordering overlap between the two. Deployment per Miner is therefore the
scientifically cleaner representative of the local participant-relationship
question. Evaluating it first prevents the later Share-Imbalance result from
being interpreted without a predictive reference for its nearest ordering.

### Expected information gain

**High, after Miner Count.** The evaluation would answer whether a
candidate-local relationship contributes information not demonstrated by
direct Deployment. Together with the preceding Miner Count result, it would
also distinguish three broad possibilities:

- information associated with direct membership ordering;
- information associated with the local Deployment–Miner relationship; or
- no demonstrated information in either ordering.

These are scientific distinctions only. They do not select an engine input or
combined procedure.

### 3.3 Third — Signed Deployment–Miner Share Imbalance

### Scientific question to resolve

Does exact Signed Deployment–Miner Share Imbalance contain decision-time
information about the eventual winning square, and does its predictive result
add scientifically distinct evidence beyond Deployment per Miner?

The second clause describes the reason for ordering the research. It does not
define an incremental-effect test or protocol.

### Scientific dependencies

Share Imbalance depends on:

- Finding 004 as its valid outcome-blind characterization;
- Finding 001 as the direct-Deployment predictive reference;
- the completed Miner Count predictive finding as the direct-membership
  reference; and
- the completed Deployment-per-Miner predictive finding as the nearest
  relationship-ordering reference.

The last dependency is essential for interpretation. Share Imbalance and
Deployment per Miner have identical average-rank vectors in `50.1340%` of
eligible decisions. Their population-average pairwise disagreement is only
approximately `0.7635` pairs, and Top-1 membership differs in `3.0147%` of
decisions. A Share-Imbalance predictive result cannot be interpreted as new
family-level information without first knowing the result of its closest
existing ordering.

### Why it is third

Share Imbalance is scientifically distinct but has the lowest expected
incremental information gain of the three evaluations. It differs extensively
from Deployment and Miner Count, yet those comparisons largely mirror the
relationship structure already represented by Deployment per Miner. Its
unique contribution lies in the 8,932 decisions with strict differences from
Deployment per Miner, not in the 8,980 identical decisions.

Evaluating it last makes the scientific question precise: after the direct
Miner Count and representative local relationship are understood, does the
distribution-relative form change the predictive conclusion?

### Expected information gain

**Moderate and conditional.** The evaluation is still necessary because the
orderings are not equivalent. Its principal value is incremental:

- a result materially different from Deployment per Miner would show that
  small ordering changes can alter the family-level predictive conclusion;
- a concordant result would establish reproducibility across two closely
  related participant relationships, without proving that they are
  independent signals; and
- an inconclusive result would bound the uncertainty associated with the
  relatively sparse differences between them.

The roadmap does not predeclare what constitutes a materially different
predictive result. That belongs to future prospective governance and protocol
work, not this planning document.

## 4. Dependency graph

```text
Finding 001 + Finding 003
            |
            v
Predictive evaluation 1: Miner Count
            |
            |  + Finding 002
            v
Predictive evaluation 2: Deployment per Miner
            |
            |  + Finding 004
            v
Predictive evaluation 3: Signed Share Imbalance
```

This graph expresses scientific interpretation order. It does not authorize
execution and does not imply that one signal's observed performance may be
used to modify another signal or its future protocol.

## 5. Cross-evaluation scientific dependencies

For the sequence to produce cumulative knowledge, future protocols should be
independently governed while preserving comparability at the scientific
boundary. At minimum, the future research must retain consistent meanings for:

- the frozen decision-time boundary;
- the eligible Replay population and explicit exclusions;
- protocol-revision provenance;
- chronology and decision-distance controls;
- lifecycle completeness;
- outcome availability and provenance;
- uninformed comparator roles; and
- positive, negative, inconclusive, and invalid dispositions.

This list records dependencies already made material by Findings 001–004. It
does not select values, algorithms, statistical procedures, or artifact
contracts for any future experiment.

Results should remain individually interpretable. A later evaluation may use
earlier findings as scientific context, but it must not redefine an earlier
question, rescue a negative result, select a post-hoc subgroup, or convert
ordering novelty into assumed predictive value.

## 6. Expected cumulative information gain

| Evaluation | Primary uncertainty resolved | Structural independence | Expected information gain | Why it changes the family map |
| --- | --- | --- | --- | --- |
| 1. Miner Count | Whether the second fundamental participant ordering contains predictive information | Highest | High | Completes predictive evidence for both atomic participant measurements |
| 2. Deployment per Miner | Whether the local relationship contributes information beyond direct Deployment and Miner Count | High | High | Tests the representative relationship ordering |
| 3. Signed Share Imbalance | Whether the distribution-relative relationship changes the conclusion of its nearest ordering | Moderate because of strong overlap | Moderate, conditional | Tests incremental evidence within the relationship cluster |

After all three valid evaluations, the repository would be able to distinguish
among:

- evidence confined to a direct fundamental ordering;
- evidence confined to a participant relationship;
- concordant evidence across structurally different orderings;
- redundant results across closely overlapping relationships;
- negative evidence across the complete core family; and
- unresolved cases requiring additional data or analysis.

None of these possibilities is assumed in advance.

## 7. Relationship to decision-engine research

Decision-engine design should remain downstream of this roadmap. Until the
three evaluations are complete, the repository lacks evidence for:

- including Miner Count as a decision signal;
- including Deployment per Miner as a decision signal;
- treating Share Imbalance as incremental to Deployment per Miner;
- resolving conflict among the orderings;
- combining signals; or
- excluding a signal after a valid predictive result.

The roadmap's purpose is to produce the evidence needed for those later
choices. It does not make them.

## 8. Recommendation

Perform predictive evaluation in this order:

1. **Miner Count** — highest structural independence and the remaining
   fundamental participant-state axis;
2. **Deployment per Miner** — the representative local relationship between
   the two fundamental measurements; and
3. **Signed Deployment–Miner Share Imbalance** — the distribution-relative
   relationship whose incremental meaning depends on the Deployment-per-Miner
   result.

This ordering maximizes early scientific information gain, preserves a clear
dependency chain from fundamental measurements to relationships, and defers
the most overlapping signal until its nearest scientific comparator is
understood. It authorizes no implementation, protocol, evaluation, or
decision-engine work.
