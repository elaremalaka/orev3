# Discovery Session 4 — Behavioral Dimensions

## Status

Read-only exploratory investigation. No code, clustering, machine learning,
prediction, strategy design, or formal Research Question creation was
performed.

## 1. Objective

This session distinguishes two different claims about the cumulative archived
RFC-012 replay dataset:

1. an observed state or state change reflects ORE protocol activity; and
2. the recorded timing, concentration, or frequency of that activity reflects
   an intrinsic property of an ORE round.

The first claim is often well supported: deployed-lamport and miner-count
vectors are decoded protocol state. The second requires more caution because an
observer samples that state at discrete times. Sparse sampling can combine
several unobserved changes into one recorded transition, omit intermediate
leaders, and make two separately timed changes appear synchronized.

The assessment covers every behavioral dimension described in
[Discovery Session 3](discovery-session-003.md) and uses the lifecycle and
future-information boundaries inventoried in
[Discovery Session 1](discovery-session-001.md). The three progressions in
[Discovery Session 2](discovery-session-002.md) provide concrete examples but
do not determine the population-level conclusions.

**Result:** the observed state vectors and their differences are evidence of
protocol behavior, but observation density, exact transition concentration,
exact synchronization, and change-event counts are measurement-dependent.
Leader/order separation and a recurring late quiet portion remain visible
under dense cadence, although their exact duration and change counts are still
sampling-dependent.

## 2. Behavioral dimensions

### 2.1 Assessment method

The population remains the 17,912 replay rounds classified as `complete` in
Discovery Session 3. Their 1,344,065 snapshot references were retained in
canonical lifecycle order. No outcome value was used to define a behavioral
measurement. Outcome capture mode was used only as collection provenance after
the measurements existed.

The following objective controls were compared:

| Control | Complete rounds | Purpose |
|---|---:|---|
| Dense cadence: maximum gap below 2 seconds | 15,554 | Describes behavior with approximately regular sampling |
| Intermediate cadence: maximum gap from 2 to below 10 seconds | 170 | Separates small irregularities from large gaps |
| Sparse cadence: maximum gap at least 10 seconds | 2,188 | Tests sensitivity to accumulated unobserved change |
| Initial deployment and miner vectors both zero | 6,635 | Tests sensitivity to retained lifecycle start state |
| Initial vectors not both zero | 11,277 | Tests behavior after nonzero state is already visible |

The median maximum gap is 1.0101 seconds in the dense group and 25.3237
seconds in the sparse group. A comparison is treated as evidence of
measurement influence when the same descriptive metric changes sharply across
these controls. It does not establish why the cadence changed.

### 2.2 Movement concentration and timing

Every complete replay round contains recorded deployment and miner movement.
That establishes that the decoded protocol vectors change during the retained
lifecycle. The amount assigned to any one **recorded transition**, however, is
the net difference between two samples rather than a record of every protocol
action between them.

| Measurement | Dense cadence median | Sparse cadence median |
|---|---:|---:|
| Largest deployment-transition share | 0.4212 | 0.6326 |
| Largest miner-transition share | 0.1934 | 0.4011 |
| Opening-loaded strict motif | 32.1% | 8.6% |
| Distributed four-quarter strict motif | 51.9% | 6.5% |

The increase in largest-transition share and collapse of the distributed
four-quarter motif under sparse cadence show that exact burst size and timing
are observer-sensitive. Sparse samples accumulate changes that dense samples
would record separately.

Lifecycle start state is another strong influence. Initially zero rounds have
median largest-transition shares of 0.5529 for deployment and 0.8205 for miner
counts. Initially nonzero rounds have medians of 0.3868 and 0.1532. The strict
opening-loaded motif appears in 75.4% of initially zero rounds but 1.9% of
initially nonzero rounds. Zero is an actual observed protocol state, but whether
the retained lifecycle begins before or after the first nonzero state is also a
coverage boundary.

**Assessment:** the existence and direction of vector movement are protocol
observations. Exact dominant quarter, largest-transition share, and membership
in opening, closing, burst, or distributed motifs are mixed measurements whose
values depend materially on cadence and lifecycle start.

**Confidence:** high that the underlying movement is protocol behavior;
moderate that broad uneven-versus-distributed movement remains meaningful
within a fixed dense regime; low that the exact Session 3 motif boundaries are
intrinsic round properties.

### 2.3 Deployment leader stability

At any recorded observation, the square or tied squares with maximum deployed
lamports are determined directly from the decoded 25-square vector. That
instantaneous leader state is protocol evidence.

Across complete rounds, deployment leader changes have a median of 2 in both
the dense and sparse groups. Full deployment-order changes have medians of 9
and 7 respectively. Stable deployment leadership with changing lower order
appears in 2,106 of 15,554 dense rounds (13.5%) and 210 of 2,188 sparse rounds
(9.6%). It therefore persists under regular sampling and is not created only
by large gaps.

The exact number and time of leader changes remain sampling-dependent. A gap
can hide a temporary leader and retain only the states on either side. The
strict “zero leader changes” motif also depends on lifecycle start: it occurs
in none of the initially zero rounds because the all-square zero tie necessarily
changes when deployment begins, but in 2,342 initially nonzero rounds.

**Assessment:** instantaneous deployment leadership and the separation between
leader stability and lower-rank movement reflect protocol state. Counts of
leader changes and strict whole-lifecycle stability also reflect cadence and
the retained starting state.

**Confidence:** high for the instantaneous leader; moderate for the broad
stable-leader/changing-order dimension; low for treating an exact leader-change
count as intrinsic.

### 2.4 Miner leader stability

The same distinction applies to miner counts. The instantaneous tied or sole
miner leader is computed from the decoded 25-square miner-count vector and is
protocol evidence. Miner leader changes have a median of 4 in dense rounds and
2 in sparse rounds; full miner-order changes have medians of 15 and 10.
Sparse sampling therefore omits more visible intermediate miner states.

Stable miner leadership with changing lower order appears in 1,034 dense
rounds (6.6%) and 174 sparse rounds (8.0%), so the leader/order distinction is
not confined to one cadence regime. As with deployment, the strict zero-change
definition appears in none of the initially zero rounds and in 1,219 initially
nonzero rounds.

**Assessment:** instantaneous miner leadership is protocol state. The broad
leader/order distinction recurs under dense observation, but exact transition
counts and whole-lifecycle stability are cadence- and boundary-dependent.

**Confidence:** high for the instantaneous leader; moderate for the broad
dimension; low for exact change counts as intrinsic properties.

### 2.5 Complete ordering stability

The ordering at one observation is a deterministic description of the decoded
vector. Square identifier is used only to present exact ties consistently; it
does not turn an equal value into a protocol preference. An ordering change
between observations is therefore evidence that the two sampled protocol
states differ.

The number of observed changes is not the number of protocol reorderings.
Dense rounds have median deployment/miner order-change counts of 9/15; sparse
rounds have medians of 7/10. Intermediate orders can occur and disappear
between sparse samples. Ties also make a whole-order comparison sensitive to
small observed changes among lower-ranked squares even when leadership is
unchanged.

**Assessment:** each sampled partial order, including its ties, reflects
protocol state. The presence of lower-rank movement is supported, but its exact
event count and timing are observation-dependent.

**Confidence:** high for snapshot-level order and ties; moderate for relative
statements such as “lower ranks changed while the leader remained”; low for
exact whole-round order-change counts as intrinsic.

### 2.6 Deployment/miner synchronization

Session 3 defined synchronization over **recorded transitions**: among
transitions where either vector changes, it measured how often both change.
That definition is directly sensitive to the interval between samples.

| Cadence group | Fully synchronized rounds | Median synchronization |
|---|---:|---:|
| Dense, maximum gap below 2 seconds | 162 of 15,554 (1.0%) | 0.8500 |
| Sparse, maximum gap at least 10 seconds | 2,130 of 2,188 (97.3%) | 1.0000 |

A long interval can contain a deployment change and a miner change at
different unobserved times, yet both appear in the same before/after
transition. The archive contains no event-level transaction sequence that
could establish their actual simultaneity.

**Assessment:** the two vectors often differ between the same pair of sampled
states, but exact synchronization is primarily a property of observation
spacing in this archive. It is not established as an intrinsic round class.

**Confidence:** high that cadence materially influences the recorded metric;
low that exact synchronization reflects protocol simultaneity.

### 2.7 Quiet intervals and quiet suffixes

A quiet observed interval means two consecutive samples have identical
deployment and miner vectors. Under dense cadence this is direct evidence that
no net vector change is visible at those endpoints. It does not prove that no
intermediate action occurred and reversed between them.

Quiet-suffix share is unusually stable across the cadence controls: its median
is 0.1841 in dense rounds and 0.1845 in sparse rounds. A share from 0.10 to
below 0.25 occurs in 99.7% of dense rounds and 99.3% of sparse rounds. This
supports a recurring recorded late quiet portion. It does not establish an
intrinsic exact duration because both the last visible change and the recorded
lifecycle endpoint depend on sampling and coverage. The only suffix occupying
at least half of a complete round remains Round 343,458; it is not recurring.

**Assessment:** repeated identical dense observations provide protocol-state
evidence of visible quiet. The recurring broad late-quiet tendency is supported
across cadence regimes. Exact quiet duration, the beginning of a quiet interval,
and the extreme long-quiet label remain measurement-dependent.

**Confidence:** moderate for a broad late quiet portion; low for exact duration
or a distinct long-quiet class.

### 2.8 Observation density and spacing

Observation count, timestamp spacing, and maximum gap are properties of the
collection record. The protocol supplies round state and slot boundaries, but
it does not prescribe this repository's polling timestamps.

Most complete rounds have 77–80 observations near one-second spacing. The
2,188 large-gap rounds form a later chronological regime, and all 1,937
complete rounds with `post_transition_predecessor` outcome capture are in that
group. Capture-mode-null rounds have a median of 78 observations and only 8 of
14,714 have a gap of at least 10 seconds; post-transition-capture rounds have a
median of 54 and all have such a gap.

**Assessment:** observation density and spacing are measurement properties,
not intrinsic ORE round behavior.

**Confidence:** high.

## 3. Artifact assessment

### 3.1 Dimension-by-source matrix

“Influenced” below means the archive provides direct comparative evidence that
the measurement changes with that source. “Possible” means the architecture
can affect what is observed, but this dataset does not isolate or quantify the
effect. “Excluded” means the architecture prevents that source from changing
the normal replay snapshot sequence.

| Behavioral dimension | Protocol-state evidence | Cadence influence | Lifecycle-coverage influence | Capture mode / RFC-012 path | Replay-construction influence | Overall confidence |
|---|---|---|---|---|---|---|
| Existence of deployment/miner movement | Direct vector differences | Affects resolution, not existence in complete rounds | Possible at boundaries | No direct outcome-path effect | Does not invent changes | High protocol signal |
| Exact movement concentration and dominant quarter | Based on real endpoint states | Strongly influenced | Strongly influenced by initial state and observed span | Associated with cadence regime | Quartering uses retained observed span | Low as an intrinsic exact value |
| Deployment leader at one snapshot | Direct decoded vector | None for that snapshot | Determines which snapshots are available | Excluded from outcome-only evidence path | Deterministic derivation only | High protocol signal |
| Deployment leader-change count | Real sampled changes | Intermediate leaders can be missed | Initial all-square tie changes classification | Associated through cadence | Counts retained transitions only | Moderate broad signal; low exact count |
| Miner leader at one snapshot | Direct decoded vector | None for that snapshot | Determines available states | Excluded from outcome-only evidence path | Deterministic derivation only | High protocol signal |
| Miner leader-change count | Real sampled changes | Stronger count reduction under sparse cadence | Initial all-square tie changes classification | Associated through cadence | Counts retained transitions only | Moderate broad signal; low exact count |
| Complete ordering at one snapshot | Direct decoded vector; ties preserved | None for that snapshot | Determines available states | Excluded from outcome-only evidence path | Deterministic tie presentation | High protocol signal |
| Complete order-change count | Real sampled differences | Intermediate orders can be missed | Start/end state bound the count | Associated through cadence | Counts adjacent retained snapshots | Moderate broad signal; low exact count |
| Exact deployment/miner synchronization | Endpoint changes are real | Dominated by gap length | Coverage determines adjacent pairs | Strong association with post-transition regime | Adjacent-pair construction exposes the effect | Low intrinsic confidence |
| Quiet observed interval | Identical sampled endpoint vectors | Duration and detection depend on spacing | Endpoint coverage limits the interval | Associated through cadence | No interpolation between samples | Moderate for visible quiet |
| Exact quiet-suffix duration | Based on last visible change | Influenced | Influenced by final retained boundary | No direct outcome attachment effect | Uses retained observed duration | Low as an exact intrinsic value |
| Observation density and spacing | None beyond protocol round duration | It is the cadence measurement | Coverage sets count and span | Strong regime association | Preserved, not generated | High confidence it is an artifact |

### 3.2 Observation cadence

Cadence is the largest demonstrated artifact source. Sparse sampling raises
single-transition concentration, lowers visible ordering transitions, and
almost deterministically produces the Session 3 exact-synchronization metric.
These are expected consequences of comparing endpoint states over longer
intervals; no interpolation is available to recover the omitted path.

### 3.3 Lifecycle coverage

Restricting the population to `complete` removes known partial boundary
lifecycles, but it does not make every lifecycle identical. Complete rounds can
have 14–146 observations and can begin with either zero or nonzero deployment
and miner vectors. Consequently:

- the initial all-square tie is present in some lifecycles and absent in
  others;
- the first recorded transition can include initialization-scale accumulated
  movement; and
- change counts and elapsed-time quarters are bounded by the retained first and
  last observations.

The strong initial-zero comparisons show that coverage/state-at-entry must be
held distinct from an intrinsic behavioral class.

### 3.4 Capture mode and the RFC-012 observation path

The archive shows a strong association between
`post_transition_predecessor` capture and sparse normal observation histories.
That association is evidence of a collection regime, not evidence that outcome
capture changes protocol behavior.

RFC-012 keeps post-transition evidence outside the normal snapshot stream. The
Dataset Builder freezes normal decision snapshots before discovering or
parsing RFC-012 evidence, then attaches accepted evidence only at the outcome
boundary. Therefore capture mode cannot alter deployment vectors, miner
vectors, snapshot ordering, Replay, or `DecisionContext` through replay
construction. This exclusion is specified in the
[Phase 3 walkthrough](../rfc012/phase3-walkthrough.md) and the
[Phase 5 walkthrough](../rfc012/phase5-walkthrough.md).

The supported runtime invokes the single Phase 2 transition processor after
successor snapshot persistence and before the next normal observer iteration.
That call can occupy wall-clock time in the collection loop. The archive does
not isolate its duration from other runtime or environmental causes, so this
session records a **possible timing influence and a strong empirical
association**, not a causal attribution.

### 3.5 Replay construction

Replay construction canonically orders and references accepted normal
snapshots. It does not interpolate missing observations, create intermediate
states, or merge post-transition evidence into the snapshot side. The
behavioral calculations in Sessions 2–4 operate on those retained adjacent
states.

Replay construction therefore preserves the measurement artifacts already
present in raw collection:

- a long raw observation gap remains a long gap;
- multiple unobserved changes remain one endpoint difference;
- lifecycle boundaries determine the measured span; and
- outcome capture remains separate.

It can influence which raw observations belong to an accepted lifecycle and
whether the lifecycle is marked complete, but it does not create the decoded
behavioral values assessed here.

## 4. High-confidence behavioral dimensions

The following conclusions are supported without treating cadence-dependent
summaries as protocol events:

1. **Snapshot-level deployment state.** Each retained 25-square
   deployed-lamport vector is an observed protocol state.
2. **Snapshot-level miner state.** Each retained 25-square miner-count vector
   is an observed protocol state.
3. **Instantaneous leadership and ties.** Leaders derive directly from each
   vector, with ties retained rather than resolved into a false sole leader.
4. **Instantaneous ordering.** The partial ordering at a snapshot reflects the
   observed values; square identifier affects presentation of exact ties only.
5. **Movement exists across all complete lifecycles.** Every complete round has
   at least one recorded change in deployment or miner state.
6. **Leader stability and lower-order stability are different dimensions.**
   Stable leadership with changing lower ranks recurs within the dense-cadence
   population for both vectors.
7. **Observation density is not intrinsic round behavior.** It is collector
   measurement and varies strongly by chronology and capture regime.
8. **RFC-012 outcome evidence does not enter behavioral snapshots.** The
   outcome-only join occurs after the immutable decision-snapshot freeze.

These are high-confidence statements about observed state and architectural
separation. They do not assert causes, predictive value, or discrete round
classes.

## 5. Low-confidence behavioral dimensions

The following should not be treated as intrinsic round properties on the
current evidence:

- exact full-synchronization status;
- exact counts of deployment, miner, leader, or ordering changes;
- exact largest-transition movement share;
- exact dominant elapsed-time quarter;
- strict membership in opening-loaded, closing-loaded, burst, or distributed
  motifs;
- initialization-dominated behavior without conditioning on retained initial
  state;
- exact quiet-interval or quiet-suffix duration;
- a distinct long-quiet-suffix class; and
- observation count, density, or spacing.

These measurements remain valid descriptions of the archived records. The low
confidence applies only to interpreting them as intrinsic protocol behavior.

## 6. Remaining uncertainties

The archive cannot determine:

- the number or ordering of protocol actions between consecutive observations;
- whether deployment and miner changes inside one recorded transition occurred
  at the same instant;
- whether temporary leaders or rank orders appeared during large gaps;
- whether an identical pair of sampled vectors conceals offsetting intermediate
  changes;
- the independent contribution of RFC-012 processing, RPC latency, host load,
  or other runtime conditions to the later sparse cadence regime;
- whether the first zero state is the protocol round's earliest possible state
  or merely the earliest state retained for that lifecycle;
- exact protocol-time movement concentration without a uniformly observed
  event stream; or
- whether the narrow quiet-suffix distribution is caused by protocol timing,
  observer timing relative to Board advancement, or both.

No missing interval is reconstructed or inferred in this session.

## 7. New questions raised

The following are informal discovery prompts, not formal Research Questions:

- Whether broad movement-concentration descriptions remain stable when only
  dense-cadence, initially nonzero lifecycles are compared.
- Whether leader/order separation has the same frequency across chronological
  dense-cadence windows.
- Whether quiet-suffix proportions remain narrowly distributed when lifecycle
  start and end coverage are held constant.
- Whether collector timing records can separate RFC-012 transition-processing
  time from RPC and host-runtime delay without changing observation semantics.
- Whether slot-based spacing and wall-clock spacing lead to the same artifact
  assessment.
- Whether any synchronization statement survives when limited to adjacent
  observations with near-identical spacing.

These prompts identify unresolved descriptive boundaries only. They do not
propose prediction, strategy, or implementation work.
