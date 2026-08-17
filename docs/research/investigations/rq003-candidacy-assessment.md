# RQ-003 Candidacy Assessment

## Status

Research candidacy assessment only. This document does not create or draft
RQ-003, propose a strategy, perform predictive analysis, or modify an RFC.

## 1. Objective

This assessment determines whether the four completed Discovery Sessions have
produced enough evidence to justify formalizing a third Research Question.

The assessment uses only:

- [Discovery Session 1 — Dataset Inventory](../notebook/discovery-session-001.md);
- [Discovery Session 2 — Round Evolution](../notebook/discovery-session-002.md);
- [Discovery Session 3 — Round Taxonomy](../notebook/discovery-session-003.md); and
- [Discovery Session 4 — Behavioral Dimensions](../notebook/discovery-session-004.md).

The standard is not whether the archive already answers a predictive question.
The standard is whether it identifies one coherent, testable next question,
defines the information boundary needed to investigate it, and exposes the
measurement limitations that the investigation must control.

## 2. What has been learned

### 2.1 The available research population is known

The archived RFC-012 checkpoint is a cumulative dataset, not a 48-hour-only
sample. It contains:

- 18,653 replay rounds;
- 1,390,766 referenced snapshots;
- 17,912 complete and 741 incomplete lifecycles;
- 3,507 locally observed outcomes;
- no enriched outcomes in the archived build; and
- 15,146 missing outcomes.

The observations span approximately 19 days, 20 source files, and 10 collector
sessions. Dataset integrity is valid. This is sufficient to identify the
available population and its principal limitations before a formal analysis is
specified.

### 2.2 The decision-time and outcome boundaries are explicit

Discovery Session 1 inventories the contemporaneous Board, Treasury, Round,
timing, deployment, and miner-count fields available at each observation. It
also identifies finalized entropy and `winning_square` as outcome-only facts.

RFC-012 evidence and historical enrichment join only after the immutable
decision-snapshot freeze. They cannot enter Replay snapshots or
`DecisionContext`. The Discovery Sessions therefore establish a usable
separation between candidate explanatory inputs and the eventual outcome
label.

### 2.3 Round state has observable temporal structure

Discovery Sessions 2 and 3 establish that complete rounds contain changing
deployment and miner-count vectors, leadership changes, lower-order movement,
quiet portions, and differing movement concentration. The full complete-round
scan found:

- recorded movement in every complete lifecycle;
- recurring stable-leader/changing-order behavior;
- recurring distributed and initialization-dominated movement motifs; and
- continuous rather than clearly separated distributions for many timing and
  concentration measurements.

These findings justify asking whether contemporaneous state carries
information. They do not establish that it does, and they do not justify a
strategy.

### 2.4 A discrete behavioral taxonomy is not supported

Discovery Session 3 found overlapping motifs, smooth measurement ranges, 3,900
multi-motif rounds, and 3,847 rounds outside its broad timing probes. It did
not find descriptive evidence for a small set of mutually exclusive natural
round classes.

Behavioral clustering or archetype prediction therefore has not emerged as
the best-supported immediate direction.

### 2.5 Measurement artifacts are now identified

Discovery Session 4 separates protocol-state evidence from trajectory
measurements affected by collection:

- snapshot-level deployment and miner vectors, leaders, ties, and orders are
  direct protocol observations;
- exact transition counts, burst shares, dominant quarters, and quiet
  durations depend on cadence and lifecycle coverage;
- exact deployment/miner synchronization is dominated by observation spacing;
  and
- observation density and spacing are collection properties, not intrinsic
  round behavior.

The archive contains 15,554 complete rounds with maximum gaps below two
seconds and 2,188 with gaps of at least ten seconds. Exact synchronization is
1.0% in the dense group and 97.3% in the sparse group. Initially zero and
initially nonzero lifecycles also have sharply different recorded movement
concentration. These are concrete validity controls for any subsequent formal
analysis.

## 3. What remains unknown

The Discovery Sessions do not determine:

- whether any decision-time field is associated with or predictive of the
  finalized winning square;
- whether any apparent relationship generalizes chronologically beyond the
  observations used to identify it;
- whether an apparent relationship survives controls for cadence, lifecycle
  coverage, initial state, capture mode, collector session, and chronology;
- whether the outcome-observed population represents the missing-outcome
  population;
- whether current-round and post-transition-predecessor outcome populations
  yield compatible results;
- whether deployment and miner histories add information beyond static or
  seeded-random baselines;
- how uncertainty changes across round and observation positions;
- whether any measured improvement is large enough to be practically
  distinguishable from sampling variation; or
- whether a result on this cumulative checkpoint reproduces on a later,
  independently archived dataset.

The archive also cannot reconstruct protocol actions between snapshots.
Accordingly, event-level simultaneity, exact numbers of intermediate leader
changes, and exact burst timing remain unsuitable foundations for the primary
question.

## 4. Has one coherent question emerged?

Yes. The discovery chain naturally points toward testing whether strictly
decision-time ORE state contains reproducible out-of-sample information about
the winning square beyond permanent deterministic and seeded-random baselines.

This is coherent because the Discovery Sessions have established:

1. a well-defined immutable replay population;
2. a documented decision-time input surface;
3. a separately attached winning-square outcome;
4. observable variation in contemporaneous round state;
5. deterministic replay and chronological ordering; and
6. the cadence, lifecycle, and outcome-provenance controls required to avoid
   mistaking measurement regimes for protocol signal.

The question has **not** been answered. Its candidacy follows from the defined
inputs, label, controls, and uncertainty—not from a preliminary claim of
predictability.

## 5. Competing questions

Several narrower questions remain visible:

- whether outcome availability is selectively associated with chronology,
  cadence, or lifecycle state;
- whether broad behavioral dimensions remain stable within one dense-cadence
  regime;
- whether quiet-suffix regularity persists under uniform lifecycle coverage;
- whether collector timing can explain the later sparse-cadence regime; and
- whether discrete behavioral classes exist under measurement-standardized
  inputs.

These do not prevent a coherent RQ-003 candidacy:

- outcome availability and cadence/lifecycle effects are required validity
  checks for the primary investigation;
- collector-runtime causation is an infrastructure question rather than a
  prerequisite for using the already identified dense subset;
- quiet-suffix regularity is one descriptive dimension, not a competing
  outcome question; and
- the current evidence argues against making taxonomy or clustering the next
  primary direction.

The competing questions should therefore be recorded as limitations,
stratification requirements, or later discovery candidates. They do not need
to be answered before RQ-003 is formalized.

## 6. Is additional discovery required first?

No additional open-ended Discovery Session is required before formalization.
Sessions 1–4 have completed the necessary progression:

- inventory the available information;
- observe representative temporal evolution;
- test whether recurring patterns justify a taxonomy; and
- separate protocol state from collection and replay artifacts.

Further descriptive work without a formal question would likely repeat the
same dimensions or introduce thresholds after inspecting the data. The next
step should instead predeclare the eligible population, features, controls,
evaluation sequence, and interpretation rules before outcome-based analysis.

This conclusion does not mean the present archive is sufficient for every
claim. A later independent snapshot may be necessary to confirm generalization,
and missing-outcome selection must be measured. Those requirements belong
inside the formal research scope.

## 7. Recommended RQ-003 parameters

The following are candidacy recommendations, not a draft Research Question.

### 7.1 Objective

Determine whether information available at or before a decision observation
contains reproducible, chronologically out-of-sample information about the
finalized winning square beyond permanent baseline behavior, while controlling
for known cadence, lifecycle-coverage, initial-state, and outcome-availability
effects.

The objective should permit a negative result. It should not assume that any
behavioral motif, strategy, or model is useful.

### 7.2 Scope

The formal investigation should:

- use one row or decision unit whose complete round membership remains grouped;
- preserve chronological order in every development and evaluation split;
- compare only information available by the selected decision point;
- begin with high-confidence snapshot-level state and deterministic historical
  summaries using only earlier observations;
- predeclare treatment of complete and incomplete lifecycles;
- report dense and sparse cadence populations separately rather than treating
  cadence as protocol behavior;
- report initially zero and initially nonzero lifecycles separately where a
  temporal summary is sensitive to the first retained state;
- report `current_round` and `post_transition_predecessor` outcome populations
  separately as provenance controls;
- quantify how the labeled population differs from the full replay population;
  and
- preserve negative and non-generalizing results.

The scope should test information content, not allocate capital, optimize a
portfolio, infer protocol causality, or admit a strategy.

### 7.3 Success criteria

Research completion should require all of the following regardless of whether
predictability is found:

1. deterministic reproduction from an identified immutable dataset;
2. an explicit leakage audit proving every candidate input exists at or before
   the selected decision observation;
3. round-grouped chronological evaluation with no random row-level split;
4. comparison with declared permanent baselines;
5. sample sizes and uncertainty reported for every result;
6. separate results for the principal cadence, lifecycle-start, and outcome-
   capture controls;
7. explicit analysis of labeled-versus-missing outcome selection;
8. consistent evaluation definitions across all comparisons; and
9. a conclusion that distinguishes supported information, unsupported
   information, and insufficient evidence.

A positive claim should additionally require reproducible improvement on held-
out chronological rounds and consistency across the predeclared validity
controls. Exact quantitative thresholds should be declared in RQ-003 before
analysis begins; the descriptive Discovery Sessions do not supply evidence for
choosing one after the fact.

### 7.4 Required datasets

At minimum, the formal investigation should identify and pin:

- the archived RFC-012 cumulative checkpoint used by Discovery Sessions 1–4,
  including its replay dataset identity and raw observation references;
- its outcome provenance, lifecycle quality, collector-session, and cadence
  metadata for validity analysis; and
- a later independently archived replay snapshot if the intended conclusion
  includes temporal reproduction beyond the discovery checkpoint.

The current archive is sufficient to begin a bounded analysis because it has
3,507 locally observed outcomes. It is not sufficient to assume population-
wide outcome completeness: 15,146 outcomes are missing, and the complete-round
post-transition population is associated with the sparse later collection
regime. Missing outcomes must remain missing unless a separately governed
dataset version records valid enrichment.

### 7.5 Excluded information

The following must never be predictive inputs:

- `winning_square`;
- finalized entropy;
- finalized reward, settlement, motherlode, top-miner, or other outcome values;
- future observations or the final round state unavailable at decision time;
- RFC-012 post-transition evidence;
- historical enrichment values;
- outcome source, capture mode, or evidence identities;
- lifecycle-level outcome availability as a strategy-visible input;
- source file, line number, collector session, round identifier, or timestamp
  as accidental identity or chronology proxies;
- replay internals unavailable during live inference; and
- `mass`, because the audited repository data contains constant zero mass.

Outcome provenance, capture mode, cadence, session, and chronology may be used
only to define splits, audit representativeness, or report stratified results.
They must not become deployable predictive information.

### 7.6 Dependencies

Before outcome-based conclusions are accepted, RQ-003 should depend on:

- the immutable archive and dataset identity documented in Discovery Session
  1;
- the decision/outcome freeze boundary validated by RFC-012;
- deterministic, tie-aware, finite feature construction using only current and
  earlier observations;
- a completed feature audit before any model training;
- grouped chronological or walk-forward evaluation;
- permanent deterministic and seeded-random baselines;
- explicit missing-outcome and capture-regime analysis; and
- independent reproduction if the result is intended to support a later
  strategy or economic investigation.

RFC-010 Strategy Lab and RFC-011 economics remain downstream validation tools.
They are not dependencies for determining whether decision-time state contains
out-of-sample information, and economic results must not be used to redefine
the question after analysis begins.

## 8. Candidacy conclusion

The Discovery Sessions provide sufficient evidence to formalize one bounded
research question about winning-square information while preserving explicit
future-information, cadence, lifecycle, and provenance controls. They do not
support a strategy, a behavioral taxonomy, or a claim that predictability
exists.

The substantial missing-outcome population and later sparse collection regime
are serious validity constraints, but they are known, measurable, and can be
made explicit in the research design. They justify stratification and cautious
interpretation rather than another open-ended discovery session.

**Begin RQ-003.**
