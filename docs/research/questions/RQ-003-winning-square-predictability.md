# RQ-003 — Decision-Time Winning-Square Information

## Status

**Type:** Governing Research Question specification

**State:** Ready for review

**Domain:** Research

**Implementation authorized:** No

This document governs future research into whether ORE decision-time
information contains information about the finalized winning square. It is not
an RFC, design, implementation plan, feature specification, model proposal, or
strategy proposal.

## Authority

RQ-003 is derived from:

- [Discovery Session 1 — Dataset Inventory](../notebook/discovery-session-001.md);
- [Discovery Session 2 — Round Evolution](../notebook/discovery-session-002.md);
- [Discovery Session 3 — Round Taxonomy](../notebook/discovery-session-003.md);
- [Discovery Session 4 — Behavioral Dimensions](../notebook/discovery-session-004.md);
- [RQ-003 Candidacy Assessment](../investigations/rq003-candidacy-assessment.md);
- [RFC-010 — Deterministic Strategy Laboratory](../../rfcs/RFC-010-STRATEGY-LAB.md);
- [RFC-011 — ORE Deployment Economics](../../rfcs/RFC-011-ORE-DEPLOYMENT-ECONOMICS.md); and
- [RFC-012 — Observer Finalization Capture](../../rfcs/RFC-012-OBSERVER-FINALIZATION-CAPTURE.md).

If a future research procedure conflicts with this specification, the
procedure is ineligible for RQ-003 until this specification is explicitly
reviewed and revised.

## 1. Research Question

Does information that was historically available at or before a deterministic
ORE decision observation contain reproducible, chronologically out-of-sample
information about the finalized winning square beyond deterministic and
seeded-random uninformed baselines?

The question concerns information content. It does not ask which model,
strategy, deployment, or economic allocation should be used.

The purpose of RQ-003 is to determine whether decision-time state contains
predictive information. It is not to maximize predictive performance, and it
does not assume that predictability exists.

## 2. Motivation

The Discovery Sessions establish that ORE rounds contain observable temporal
variation in deployed lamports, miner counts, leadership, ordering, movement,
and quiet periods. They do not establish that any of this variation predicts
the winning square.

They also establish important measurement limits:

- snapshot-level protocol state is directly observed;
- exact transition concentration, synchronization, and change counts are
  sensitive to observer cadence;
- lifecycle start and end coverage affect temporal summaries;
- outcome availability is incomplete and associated with collection regimes;
- no discrete natural round taxonomy has been demonstrated; and
- RFC-012 outcome evidence is future information relative to the decision and
  remains outside Replay snapshots and `DecisionContext`.

A formal protocol is therefore required before outcome-based analysis begins.
Without it, future work could mistake collector cadence, lifecycle boundaries,
chronology, outcome provenance, or accidental identifiers for information
about the winning square.

## 3. Objective

The objective is to determine whether a predeclared ranking procedure using
only eligible decision-time information can rank the eventual winning square
better than both required uninformed baselines on chronologically later,
previously unused rounds.

The investigation shall:

- permit the answer to be negative;
- measure ranking quality independently from capital allocation;
- preserve the round as the independent historical unit;
- separate development from chronological confirmation;
- quantify uncertainty and sample size;
- test sensitivity to known collection and outcome-availability regimes; and
- preserve exact reproducibility from immutable inputs and recorded
  configuration.

## 4. Null Hypothesis

Within the eligible information boundary and evaluation protocol defined here,
no predeclared candidate ranking procedure demonstrates reproducible
chronologically out-of-sample winning-square ranking performance superior to
both the deterministic baseline and the seeded-random baseline.

An apparent improvement remains consistent with the null when it:

- is not present on held-out chronological rounds;
- is not distinguishable from paired round-level variation;
- depends on one cadence, lifecycle, capture, or outcome-availability regime;
- disappears on independent temporal confirmation;
- results from future information or identity leakage; or
- cannot be reproduced exactly.

Failure to reject the null is a valid research result. It does not authorize
searching for a favorable interpretation after the evaluation.

## 5. Alternative Hypothesis

At least one predeclared candidate ranking procedure using only eligible
decision-time information demonstrates reproducible, chronologically
out-of-sample winning-square ranking performance superior to both required
uninformed baselines, with the improvement remaining directionally consistent
under the required validation controls and independent temporal confirmation.

The alternative does not assert that such a procedure exists. It does not
identify a feature, model, strategy, deployment, or economic value.

## 6. Scope

RQ-003 covers:

- prediction targets consisting only of the finalized winning square among the
  25 protocol squares;
- deterministic ranking of all 25 candidate squares at a predeclared decision
  observation;
- snapshot-level contemporaneous protocol state exposed through the immutable
  `DecisionContext` boundary;
- deterministic summaries using only the selected observation and earlier
  observations of the same round;
- deterministic state learned from earlier completed rounds only, provided the
  current round's outcome remains unrevealed at decision time;
- one primary decision point per round for the primary analysis;
- separately reported secondary decision points when declared before outcome
  analysis;
- round-grouped chronological development and evaluation;
- outcome provenance, cadence, lifecycle coverage, and chronology as audit and
  stratification controls only;
- comparison against the required baselines; and
- ranking-quality evidence before deployment or economic interpretation.

If more than one decision point is examined for a round, those observations
shall remain grouped as one round for splitting and uncertainty. They shall not
be counted as independent outcomes.

## 7. Out of Scope

RQ-003 does not cover:

- selecting, designing, or implementing a model;
- specifying feature engineering;
- proposing or admitting a Strategy;
- clustering or assigning behavioral round classes;
- explaining the protocol cause of an observed association;
- causal inference;
- capital allocation or deployment capacity;
- transaction planning or inclusion;
- reward calculation, settlement, dilution, fees, ROI, or economic valuation;
- ORE-to-SOL or fiat conversion;
- portfolio optimization;
- live mining, paper mining, or production reachability;
- automatic strategy selection;
- observer, Dataset Builder, Replay, Strategy Lab, or economics redesign;
- imputing or fabricating missing outcomes; or
- treating full-history descriptive findings as deployable inputs.

## 8. Dataset Requirements

### 8.1 Immutable dataset identity

Every RQ-003 analysis shall name immutable dataset artifacts and record at
minimum:

- dataset version and cryptographic identity;
- replay version and identity;
- raw source identities;
- dataset creation timestamp;
- round and snapshot ranges;
- lifecycle completeness counts;
- observed, enriched, and missing outcome counts;
- outcome capture-mode counts;
- collector-session and source-schema coverage; and
- integrity-validation result.

The discovery dataset is the cumulative archived RFC-012 checkpoint documented
in Discovery Session 1:

- dataset version: `replay-dataset-v1`;
- dataset SHA-256:
  `7680856bc6a01f9b69be0921d6e66b3f43d5241a38e63b37871b6925c1d59ba7`;
- 18,653 replay rounds;
- 17,912 complete lifecycles;
- 3,507 locally observed outcomes; and
- 15,146 missing outcomes.

This archive may support protocol development and bounded initial evaluation.
It shall not, by itself, support a claim of independent temporal confirmation
after it has been used to choose procedures, inputs, or interpretation rules.

### 8.2 Outcome eligibility

A round is outcome-evaluable only when its finalized outcome is valid under the
dataset contract. Missing outcomes remain missing. They shall not be assigned a
winner, included as misses, or inferred from later aggregates.

Locally observed and valid historically enriched outcomes may be evaluated
when their provenance is preserved. They shall also be reported separately.
The absence of enriched outcomes in the discovery archive does not authorize
assuming that observed and enriched populations are interchangeable.

### 8.3 Lifecycle eligibility

The primary analysis shall use complete lifecycles unless the reviewed RQ-003
analysis protocol defines a narrower rule before outcomes are examined.
Incomplete lifecycles may be described or used in a separately labeled
sensitivity analysis. They shall not be silently pooled with the primary
population.

Completeness does not imply uniform cadence or observation of every slot.
Cadence and maximum-gap distributions remain required controls.

### 8.4 Independent confirmation dataset

Support for the alternative hypothesis requires an immutable chronological
confirmation snapshot containing rounds not used to:

- identify candidate inputs;
- choose a ranking procedure;
- choose a decision point;
- choose an evaluation metric;
- select thresholds; or
- formulate the interpretation.

Its identity and eligibility rules shall be fixed before its outcomes are
evaluated. Rebuilding a cumulative dataset that includes development rounds
does not make those rounds independent; the confirmation interval must be
disjoint and chronologically later.

## 9. Decision-Time Information Boundary

### 9.1 Freeze point

Decision-time state becomes immutable when Replay selects the latest eligible
normal observation at or before the predeclared decision point and constructs
the corresponding immutable `DecisionContext`.

For RQ-003, a ranking may depend only on:

- that frozen context;
- normal observations of the same round no later than that context;
- fixed configuration declared before evaluation; and
- deterministic state derived only from earlier completed rounds whose
  outcomes had already crossed RFC-010's outcome-revelation boundary.

### 9.2 Post-freeze information

After the freeze, outcome information may be used only as the label for
evaluation. RFC-012 current-round or post-transition predecessor evidence,
historical enrichment, final entropy, and the finalized winner cannot alter:

- snapshot membership or ordering;
- `DecisionContext`;
- eligible inputs;
- the ranking already produced; or
- state used for the current decision.

An adaptive procedure may update deterministic state only after the current
round's outcome is revealed, and that state may affect only later rounds.

### 9.3 Decision-point declaration

The primary decision point and its deterministic selection rule shall be fixed
before outcome-based evaluation. The rule must be expressible using eligible
timing information and must return at most one primary context per round.

If a round lacks an eligible context at that point, it shall be reported as
ineligible rather than replaced using knowledge of its outcome. Secondary
decision points require separate predeclaration and separate reporting.

## 10. Eligible Features

This section defines eligibility, not usefulness and not an engineering
recipe. No listed field is presumed informative.

An input is eligible only when all of the following are true:

1. it existed at or before the selected decision observation;
2. it is exposed by, or can be reproduced from information permitted by, the
   immutable `DecisionContext` boundary;
3. any historical component uses only earlier observations or earlier
   outcome-revealed rounds;
4. it is deterministic and finite;
5. its semantics are identical in development and evaluation; and
6. it passes a future-information and identity-leakage audit.

Eligible information categories are:

- contemporaneous protocol timing: start slot, end slot when available,
  elapsed slots, and remaining slots when available;
- contemporaneous Board state, including production-cost state exposed by
  `DecisionContext`;
- contemporaneous Treasury state exposed by `DecisionContext`;
- the 25 current deployed-lamport values;
- the 25 current miner-count values;
- active Round fields exposed by `DecisionContext`, using only their value at
  the frozen observation;
- deterministic within-observation comparisons whose inputs are all eligible;
- deterministic same-round history ending at the frozen observation; and
- deterministic prior-round state updated only after each prior outcome was
  validly revealed.

Eligibility of a category does not authorize every possible transformation.
Any concrete input set requires a separate feature audit before evaluation.

## 11. Explicitly Prohibited Features

The following shall not be used as predictive inputs, training-time shortcuts,
selection criteria informed by the current outcome, or ranking tie-breakers:

- `winning_square`;
- finalized entropy;
- finalized slot-hash or finalization indicators unavailable at decision time;
- finalized rewards, settlement totals, total vaulted, total winnings,
  motherlode, or top-miner values unavailable at decision time;
- future observations;
- a final Board or Round state not available at the decision observation;
- RFC-012 transition or post-transition predecessor evidence;
- historical enrichment payloads;
- finalized outcome source;
- finalized outcome capture mode;
- finalized outcome evidence or transition identities;
- whether the current round eventually has an available outcome;
- Replay internals unavailable during live inference;
- Dataset Builder ordering, path, or source-reference internals;
- source file, source line number, collector session identifier, or source
  schema version;
- `round_id`, timestamp, or another accidental chronology/identity proxy used
  as a predictive input;
- any value computed using later rounds or the complete dataset future;
- full-history statistics that cross the chronological evaluation boundary;
- any imputed winning square or fabricated finalized value; and
- `mass`, because the repository's audited data contains constant zero mass
  and prohibits its use as a predictive feature.

Cadence, lifecycle status, capture mode, collector session, chronology, and
outcome availability may be used to construct audit strata and describe
selection. They may not be exposed to the ranking procedure as candidate
signals under RQ-003.

## 12. Evaluation Methodology

### 12.1 Unit of evaluation

The independent evaluation unit is one ORE round with one finalized winning
square and one primary ranked ordering of all 25 squares. Every row,
observation, or square belonging to a round shall remain in the same temporal
partition.

### 12.2 Primary endpoint

The primary endpoint is mean reciprocal rank of the finalized winning square:

`MRR = mean(1 / winning_square_rank)`

Rank is one-based. The tie rule shall be deterministic, declared before
evaluation, and identical for candidate procedures and baselines. MRR is a
ranking-quality measure. It does not represent probability, capital, expected
ORE, or economic return.

### 12.3 Secondary endpoints

Secondary descriptive endpoints may include:

- mean winning-square rank;
- top-1 hit rate;
- top-3 hit rate;
- top-5 hit rate; and
- complete square-selection or rank distribution.

Secondary endpoints cannot rescue failure on the primary endpoint unless this
specification is revised before evaluation. Probability-scoring metrics are
ineligible unless a separate reviewed protocol defines a probability output;
RFC-010 preference scores express ordering only.

### 12.4 Chronological partitions

Development, validation, and confirmation partitions shall preserve round
chronology. Random row-level or random observation-level splitting is
prohibited. No later round may influence an earlier decision.

Partition boundaries, the primary decision point, candidate input set,
baseline configuration, primary endpoint, uncertainty method, and success
threshold shall be recorded before the held-out outcomes are evaluated.

Walk-forward evaluation is permitted when every fold trains or establishes
state only on earlier rounds and evaluates only later rounds. Fold results and
aggregate results shall both be reported.

### 12.5 Paired comparison and uncertainty

Every candidate procedure and baseline shall be evaluated on the exact same
eligible rounds within a comparison. Performance differences shall be paired
by round. Uncertainty shall preserve chronology and round grouping; observations
or squares from one round shall never be treated as independent samples.

The uncertainty method and decision threshold shall be fixed before held-out
evaluation. Results shall report effect sizes, uncertainty intervals, eligible
round counts, excluded-round counts, and reasons for exclusion. A point
estimate alone cannot support the alternative hypothesis.

### 12.6 Reproducibility

The research result shall record identities for:

- datasets and raw sources;
- Replay;
- decision-point rule;
- eligible-round rule;
- candidate input schema;
- candidate ranking procedure;
- baselines and random seed;
- temporal partitions;
- evaluation definitions; and
- generated results.

Identical artifacts and configuration shall reproduce identical rankings,
metrics, and exclusions.

## 13. Required Baselines

### 13.1 Deterministic uninformed baseline

The deterministic baseline ranks the 25 squares in fixed canonical square
identifier order. It receives no current-round state, historical outcome, or
future information. Its identity and tie semantics shall be immutable and
recorded.

This baseline measures performance relative to a reproducible fixed ordering.
It does not assert that square identifiers are equiprobable.

### 13.2 Seeded-random uninformed baseline

The seeded-random baseline produces a deterministic pseudorandom permutation
of all 25 squares using a seed fixed and recorded before held-out evaluation.
It receives no protocol state, outcome, outcome provenance, dataset location,
or future information.

The baseline shall be reproducible for the same experiment identity and shall
not draw a new favorable seed after results are known. If a predeclared suite
of seeds is used to characterize baseline variation, every seed and the
aggregation rule shall be fixed before evaluation and all results reported.

### 13.3 Baseline parity

Both baselines shall:

- receive the same eligible-round set;
- use the same decision points;
- use the same rank and tie definitions;
- be evaluated with the same metrics and uncertainty method; and
- remain permanent comparators in every RQ-003 result.

Additional baselines may be added only if declared before the relevant
held-out evaluation. They do not replace either required baseline.

## 14. Validation Controls

### 14.1 Chronology

Report performance by chronological partition and verify that no later
snapshot, round, label, normalization statistic, selection decision, or state
update influences an earlier ranking. Round identifier and timestamp may define
the partition but may not be predictive inputs.

### 14.2 Observation cadence

Report sample size and primary performance separately for predeclared cadence
strata, including a dense-observation population and a population containing
large gaps. The exact boundaries shall be declared before outcome evaluation
and shall not be selected for favorable performance.

Exact transition counts, synchronization, and concentration summaries require
specific scrutiny because Discovery Session 4 found them cadence-sensitive.
Any such eligible input must pass a documented stability audit across cadence
strata before contributing to a positive conclusion.

### 14.3 Lifecycle completeness and initial state

Report complete and incomplete lifecycle counts separately. The primary
analysis uses the predeclared complete-lifecycle rule. Any incomplete-lifecycle
analysis is secondary and separately labeled.

Because initially zero and initially nonzero retained lifecycles have different
recorded movement concentration, report the primary endpoint separately for
these states whenever the candidate input uses same-round history.

### 14.4 Outcome availability

Compare the labeled and missing-outcome populations using decision-neutral
metadata, including chronology, cadence, lifecycle coverage, and collector
regime. Do not impute outcomes or treat missing outcomes as misses.

A positive conclusion shall state the population to which it applies. It shall
not be generalized to all replay rounds when outcome availability prevents
that inference.

### 14.5 Capture mode and provenance

Report valid observed outcomes separately by `current_round` and
`post_transition_predecessor` capture mode. Report enriched outcomes separately
when present. Capture mode and provenance are audit variables only and remain
outside candidate inputs.

Because post-transition outcomes in the discovery archive coincide strongly
with the later sparse collection regime, capture-mode differences shall not be
attributed causally without separate evidence. Results shall identify
confounding between chronology, cadence, and capture mode.

### 14.6 Replay and future-information audit

Verify that:

- normal snapshots are frozen before RFC-012 evidence consumption;
- RFC-012 evidence never enters Replay snapshots;
- `DecisionContext` remains outcome-free;
- a ranking is immutable before outcome revelation;
- state updates occur only after the current outcome is revealed; and
- observed and enriched outcomes differ only in evaluation provenance, never
  in strategy-visible information.

Any failure invalidates the affected result.

## 15. Success Criteria

### 15.1 Protocol completion

RQ-003 is complete when its deliverables exist, every required control has been
reported, the analysis is exactly reproducible, and the result supports one of
three explicit dispositions:

- alternative supported;
- null not rejected; or
- evidence insufficient.

Completion does not require a positive finding.

### 15.2 Support for the alternative hypothesis

The alternative hypothesis is supported only when all of the following hold:

1. the candidate procedure and inputs were fixed before held-out evaluation;
2. all inputs pass the decision-time and leakage audits;
3. primary MRR exceeds both required baselines on the same chronologically
   held-out rounds;
4. the predeclared paired uncertainty result excludes no improvement over each
   baseline at the predeclared decision threshold;
5. the direction of improvement is consistent across chronological folds and
   the principal cadence, lifecycle, initial-state, and capture-mode controls
   with sufficient eligible samples;
6. the result reproduces deterministically;
7. the improvement is confirmed on a disjoint, chronologically later immutable
   dataset not used for procedure selection; and
8. the conclusion is limited to populations supported by outcome availability.

This specification deliberately does not set a numeric effect-size or
uncertainty threshold from the Discovery Sessions. Those sessions did not
perform predictive analysis. A reviewed analysis protocol must fix those
values before any held-out outcome is evaluated.

### 15.3 Null not rejected

The null is not rejected when the protocol is valid and completed but one or
more positive-evidence criteria are not met. This outcome shall be preserved
and reported without changing the primary endpoint or controls after seeing
results.

### 15.4 Evidence insufficient

Evidence is insufficient, rather than negative, when validity cannot be judged
because of inadequate eligible outcomes, unresolved selection bias,
non-comparable regimes, missing independent confirmation, or another declared
data limitation. The insufficiency and the exact unresolved criterion shall be
reported.

## 16. Failure Criteria

An RQ-003 result is invalid if any of the following occurs:

- future or outcome information enters a predictive input;
- RFC-012 evidence enters a Replay snapshot or `DecisionContext`;
- the winner or outcome availability influences decision-point or round
  selection;
- rows, observations, or squares from one round cross temporal partitions;
- a random row-level split is used;
- later-round statistics or state influence earlier rankings;
- missing outcomes are fabricated, imputed, or counted as misses;
- outcome provenance is discarded;
- cadence, lifecycle status, capture mode, session, chronology, or accidental
  identifiers become predictive inputs;
- baseline seeds, metrics, thresholds, partitions, or primary interpretations
  change after held-out results are known;
- the candidate and baselines are evaluated on different round populations;
- uncertainty treats observations or squares from the same round as
  independent outcomes;
- a result cannot be reproduced from recorded identities;
- only a favorable secondary endpoint is reported after primary failure;
- discovery and confirmation intervals overlap in a way that informs procedure
  selection; or
- economic performance is used as a substitute for the RQ-003 ranking
  criterion.

An invalid result provides no evidence for either hypothesis and must be
corrected or repeated under a reviewed protocol.

## 17. Deliverables

RQ-003 requires:

1. a pre-analysis protocol recording dataset identities, eligibility rules,
   decision point, inputs, temporal partitions, baselines, metrics,
   uncertainty method, and decision threshold;
2. a dataset and outcome-provenance inventory for every analyzed snapshot;
3. a decision-time feature audit demonstrating eligibility, deterministic
   ordering, finite values, tie handling, and absence of future information;
4. a reproducible analysis artifact that consumes immutable datasets rather
   than live systems;
5. baseline and candidate rankings for the same eligible rounds;
6. a validation-control report covering chronology, cadence, lifecycle
   completeness, initial state, outcome availability, capture mode, and
   provenance;
7. a primary results report with effect sizes, uncertainty, sample sizes,
   exclusions, and the explicit research disposition;
8. an independent temporal confirmation report before any claim supports
   downstream strategy admission;
9. immutable identities for configurations, components, and results; and
10. preservation of negative, null, insufficient, and failed results as project
    knowledge.

No deliverable created under this specification is, by itself, a production
strategy or deployment authorization.

## 18. Future Dependencies

### 18.1 Strategy Lab

RFC-010 Strategy Lab is downstream of RQ-003. If—and only if—RQ-003 supports
the alternative hypothesis and the supporting analysis justifies a separately
reviewed candidate Strategy, Strategy Lab may test that Strategy through its
existing immutable interfaces.

Strategy Lab shall not be used to redefine RQ-003 after results are known. Its
ranking, deployment, evaluation, metrics, and registry responsibilities remain
unchanged. RQ-003 does not authorize a Strategy implementation.

### 18.2 RFC-011 Economics

RFC-011 economics is downstream of an RFC-010 experiment and consumes existing
deployment and evaluation outputs. Economic simulation may assess protocol-
native consequences only after ranking evidence and a separately authorized
deployment interpretation exist.

Economic outcomes cannot establish that decision-time state contains
winning-square information, select the RQ-003 primary endpoint, or convert a
failed ranking result into success. SOL and ORE remain separate, and missing
outcomes remain fail-closed under RFC-011.

### 18.3 Later research

Possible later work includes strategy admission, deployment comparison, and
economic evaluation. Each requires its own authorization and must preserve the
dataset identities, information boundary, provenance, and limitations recorded
by RQ-003.

## 19. Governing conclusion

RQ-003 asks whether strictly historical decision-time information supports
reproducible winning-square ranking beyond uninformed baselines. It assumes no
predictability, useful feature, model, or strategy.

All future work claiming to answer that question shall preserve this protocol's
chronology, outcome separation, baseline parity, measurement controls,
independent confirmation, and symmetric interpretation of positive, negative,
and insufficient evidence.
