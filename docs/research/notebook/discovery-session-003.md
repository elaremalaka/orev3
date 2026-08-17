# Discovery Session 3 — Round Taxonomy

## Status

Read-only exploratory investigation. No clustering, machine learning,
prediction, strategy design, or formal Research Question creation was
performed.

## 1. Objective

This session asks whether the cumulative archived RFC-012 replay dataset
contains descriptive evidence that complete ORE rounds naturally separate into
distinct behavioral classes.

The assessment begins from the information inventory in
[Discovery Session 1](discovery-session-001.md) and the three-round progression
walkthrough in [Discovery Session 2](discovery-session-002.md). It expands the
comparison to every replay round whose lifecycle coverage is `complete`.

The decision standard is deliberately conservative:

- repeated behavior is evidence for a recurring **motif**;
- a motif is not automatically a distinct class;
- overlapping motifs do not form a partition;
- smooth measurement ranges do not establish natural boundaries; and
- collection-density or lifecycle-state effects are not treated as intrinsic
  ORE round classes.

**Result:** the archive contains strong evidence for recurring behavioral
motifs, but it does **not** provide sufficient descriptive evidence that rounds
naturally fall into discrete, mutually exclusive classes.

## 2. Method

### 2.1 Population

The scan covered all 17,912 complete replay rounds and their 1,344,065 ordered
snapshot references. No outcome field was used to define behavior. Outcome
capture mode was inspected only after measurement to identify whether an
apparent pattern coincided with a collection regime.

Each raw snapshot was resolved from the archived replay round's exact source
file and line reference. Observations remained in canonical lifecycle order.

### 2.2 Descriptive measurements

For each complete replay round, the investigation recorded:

- observation count and recorded duration;
- observation density and largest observation gap;
- absolute per-transition movement in the 25-square deployed-lamport vector;
- absolute per-transition movement in the 25-square miner-count vector;
- movement assigned to four equal elapsed-time quarters;
- the share of total movement in the largest single transition;
- first and last joint movement time;
- quiet-suffix and longest-quiet-interval duration;
- complete 25-square ordering changes;
- tied or sole leader-state changes; and
- whether deployment and miner movement occurred on the same transitions.

Square order was descending by observed value with square identifier used only
to present ties deterministically. A leader state retained all squares tied for
the maximum.

### 2.3 No learned classification

No distance function, clustering algorithm, fitted breakpoint, latent class,
or outcome label was used. Broad diagnostic rules were declared solely to count
clearly described motifs:

- **opening-loaded:** at least half of both deployment and miner movement occurs
  in the first elapsed-time quarter;
- **closing-loaded:** at least half of both movements occurs in the fourth
  quarter;
- **single-transition burst:** the largest transition contains at least half of
  both movements;
- **distributed four-quarter movement:** both vectors move in every quarter and
  neither largest transition contains half of its vector's total movement;
- **long quiet suffix:** no vector changes during the final half of recorded
  duration; and
- **large observation gap:** at least one consecutive observation gap is 10
  seconds or longer.

These thresholds are descriptive probes, not claimed natural boundaries. Their
overlap and sensitivity are part of the evidence.

### 2.4 Representative-round rule

For every recurring motif, examples are the lowest, middle, and highest
`round_id` among matching rounds. This deterministic chronological spread
demonstrates recurrence without manually selecting visually striking examples.

## 3. Behavioral observations

### 3.1 Observation density is mostly regular, with a later sparse regime

| Measurement | Minimum | 10th percentile | Median | 90th percentile | Maximum |
|---|---:|---:|---:|---:|---:|
| Observations per complete round | 14 | 61 | 78 | 80 | 146 |
| Recorded duration | 62.474 s | 75.651 s | 77.544 s | 79.575 s | 146.051 s |
| Largest within-round gap | 0.805 s | 1.010 s | 1.010 s | 17.711 s | 48.397 s |

Most complete rounds contain 77–80 observations at approximately one-second
spacing. There are 2,188 complete rounds with a gap of at least 10 seconds.
Every one of the 1,937 complete rounds whose outcome capture mode is
`post_transition_predecessor` belongs to that large-gap set, and their median
observation count is 54. By contrast, capture-mode-null complete rounds have a
median count of 78 and only 8 of 14,714 contain a gap of at least 10 seconds.

The association is chronological as well. Large-gap counts are near zero in
round-id bands below 360,000, then rise to 1,328 of 1,800 complete rounds from
360,000–361,999 and all 849 complete rounds from 362,000–363,999.

**Observation:** the archive contains more than one observation-density regime.

**Inference:** observation density cannot safely serve as evidence of an
intrinsic ORE behavioral class because it is closely associated with capture
mode and chronology.

**Speculation:** none. This session does not assign a cause to that association.

### 3.2 Movement occurs in every complete round, but its timing varies

No complete replay round has zero deployment-and-miner movement. The quarter
containing the greatest deployment movement is:

| Elapsed-time quarter | Complete rounds |
|---|---:|
| First | 8,948 |
| Second | 1,875 |
| Third | 6,030 |
| Fourth | 1,059 |

The corresponding miner-movement maximum is in the first quarter for 8,830
rounds and the fourth quarter for 5,421. Deployment and miner movement share
the same dominant quarter in 10,305 rounds. The most common pairing is first /
first (7,367 rounds), followed by third-quarter deployment / fourth-quarter
miner movement (3,391 rounds).

The broad diagnostic rules identify 5,214 opening-loaded rounds and 129
closing-loaded rounds. Movement timing therefore recurs in recognizable forms,
but it is not confined to one or two positions.

**Observation:** movement concentration appears throughout the recorded
timeline, with first- and third-quarter deployment maxima most common.

**Inference:** timing supports recurring motifs but not a complete discrete
partition.

**Speculation:** none.

### 3.3 Single-transition concentration spans a broad range

The largest deployment transition accounts for:

| Distribution position | Share of total deployment movement |
|---|---:|
| 25th percentile | 0.338 |
| Median | 0.439 |
| 75th percentile | 0.572 |
| 90th percentile | 0.713 |

The observed range is 0.114–0.996. There is no empty interval around the
one-half diagnostic threshold.

Miner movement is more frequently concentrated in one transition: 6,914 rounds
have a largest miner transition containing at least half of total miner
movement. That concentration is closely associated with the lifecycle's first
state. Of 6,635 rounds whose initial deployment and miner vectors are both
zero, 6,576 have at least half their miner movement in one transition. Among
the 11,277 initially nonzero rounds, only 338 do.

There are 4,315 rounds satisfying the broad single-transition-burst rule for
both vectors; 4,113 of them begin with both vectors zero.

**Observation:** large joint bursts recur, especially when the retained
lifecycle begins with zero deployment and zero miners.

**Inference:** the initial-state boundary explains much of the apparent
separation in miner-burst concentration. The burst is a recurring lifecycle
motif, but this evidence does not establish a separate natural round class.

**Speculation:** none.

### 3.4 Movement is usually, but not always, synchronized

For each round, synchronization is the fraction of transitions with either
vector changing on which both vectors change.

| Distribution position | Synchronization fraction |
|---|---:|
| Minimum | 0.500 |
| 25th percentile | 0.818 |
| Median | 0.862 |
| 75th percentile | 0.900 |
| Maximum | 1.000 |

Deployment and miner movement are fully synchronized in 2,296 rounds. Of the
2,188 large-gap rounds, 2,130 are fully synchronized; only 166 of the 15,724
rounds without a large gap are fully synchronized.

**Observation:** both vectors usually change on the same active transitions,
and exact synchronization is concentrated among sparsely observed rounds.

**Inference:** exact synchronization in this archive is not sufficient evidence
for a natural behavioral class because coarse observation spacing combines
otherwise unobserved intermediate changes into the same recorded transition.

**Speculation:** none.

### 3.5 Leadership and complete ordering behave differently

Deployment order changes range from 0 to 22 per round, with a median of 9.
Miner order changes range from 2 to 30, with a median of 15. Deployment leader
changes have a median of 2; miner leader changes have a median of 4.

There are 2,342 rounds in which the deployment leader never changes even though
the complete deployment order does. There are 1,219 analogous miner-count
rounds. In 256 rounds neither leader changes while both complete orders change.

**Observation:** stable leadership with changing lower ranks is recurrent.

**Inference:** leader stability and ordering stability are separate behavioral
dimensions. A taxonomy based only on the leader would merge visibly different
round progressions.

**Speculation:** none.

### 3.6 Quiet suffix duration is largely continuous and narrowly concentrated

The quiet suffix begins at the last transition where either vector changes.
Its share of recorded duration has a 25th percentile of 0.181, median of 0.184,
and 75th percentile of 0.190. There are 17,850 rounds between 0.10 and 0.25,
54 between 0.25 and 0.50, and only one at or above 0.50.

That sole long-quiet-suffix round is Round 343,458 from Discovery Session 2,
whose last 56.6% of recorded duration is unchanged.

**Observation:** quiet suffixes recur, but almost all occupy a narrow continuous
band around the final fifth of recorded duration. The extreme half-round quiet
suffix does not recur.

**Inference:** the archive does not justify a distinct long-quiet-suffix class.

**Speculation:** none.

## 4. Candidate behavioral archetypes

The following are candidate **archetypes**, not asserted classes. They describe
recurring motifs with objective membership rules. They overlap and do not cover
the full population.

### 4.1 Initialization-dominated joint burst

**Objective rule:** both initial vectors are zero, and the largest transition
contains at least half of total deployment movement and half of total miner
movement.

**Frequency:** 4,113 of 17,912 complete rounds (22.96%).

**Representative rounds:** 342,104; 353,983; 362,954.

**Characteristics:**

- the lifecycle begins with zero deployment and zero miner counts;
- one transition supplies at least half of both recorded movements;
- later observations may still contain additional movement and order changes;
  and
- the motif can occur in both dense and sparse observation regimes.

The example largest-transition deployment/miner shares are 0.505/0.835,
0.636/0.860, and 0.978/0.961 respectively.

**Confidence as recurring behavior:** high. More than four thousand exact
matches occur across the archive chronology.

**Confidence as a distinct natural class:** low to moderate. Membership is
strongly determined by whether the retained lifecycle begins before or after
the first nonzero state, and the concentration measures have no demonstrated
natural breakpoint at one-half.

### 4.2 Distributed four-quarter movement

**Objective rule:** both vectors move in every elapsed-time quarter, and neither
largest transition contains half of its vector's total movement.

**Frequency:** 8,307 of 17,912 complete rounds (46.38%).

**Representative rounds:** 342,070; 351,879; 361,253.

**Characteristics:**

- movement is recorded across the complete round timeline;
- no single transition dominates either vector under the one-half rule;
- complete rankings change repeatedly; and
- leadership may remain stable or change.

The representative deployment largest-transition shares are 0.278, 0.407,
and 0.311; miner shares are 0.084, 0.129, and 0.198.

**Confidence as recurring behavior:** high. It is the largest strict motif in
this assessment and occurs across early, middle, and late round identifiers.

**Confidence as a distinct natural class:** low. Movement concentration spans
a continuous range, and 1,689 distributed rounds also have a stable deployment
leader with changing lower order.

### 4.3 Closing-loaded movement

**Objective rule:** at least half of both deployment and miner movement occurs
in the final elapsed-time quarter.

**Frequency:** 129 of 17,912 complete rounds (0.72%).

**Representative rounds:** 342,357; 356,893; 362,342.

**Characteristics:**

- both vectors have their majority movement late under the strict rule;
- leadership can remain fixed or change;
- single-transition concentration ranges from moderate to high; and
- the motif occurs under both dense and sparse observation spacing.

**Confidence as recurring behavior:** moderate. The rule matches 129 rounds
distributed across the archive rather than one isolated event.

**Confidence as a distinct natural class:** low. Eighty-nine of the 129 also
meet the distributed four-quarter rule, and 23 contain a large observation gap.

### 4.4 Stable deployment leader with changing order

**Objective rule:** zero deployment-leader changes and at least one complete
deployment-order change.

**Frequency:** 2,342 of 17,912 complete rounds (13.08%).

**Representative rounds:** 342,070; 351,614; 362,940.

**Characteristics:**

- the maximum-deployment square remains unchanged;
- lower deployment ranks continue to reorder; and
- timing and concentration vary substantially among matches.

**Confidence as recurring behavior:** high. The exact leadership/order
combination appears in more than two thousand rounds.

**Confidence as a distinct natural class:** low. The motif describes one
dimension rather than a complete progression, and 1,689 matches also satisfy
the distributed four-quarter rule.

### 4.5 Archetype overlap and noncoverage

Using opening-loaded, closing-loaded, single-transition-burst, and distributed
four-quarter rules together:

- 10,165 rounds match exactly one;
- 3,900 match more than one; and
- 3,847 match none.

The initialization-burst and distributed strict rules do not overlap because
their largest-transition conditions are mutually exclusive by definition.
Other rules overlap substantially. These results are incompatible with treating
the four probes as a discovered exhaustive taxonomy.

## 5. Counterexamples

### 5.1 Round 343,458: observation-count and quiet-suffix outlier

This maximum-count complete round has 146 observations, but neither vector
changes during its final 82.640 seconds. It is the only complete round whose
quiet suffix occupies at least half of recorded duration. It demonstrates that
high observation count does not define sustained-movement behavior and that an
extreme quiet suffix is not recurring in this archive.

### 5.2 Round 362,945: sparse observation with late captured movement

This minimum-count complete round has 14 observations and a 48.279-second
maximum gap. Its deployment movement is concentrated late, but miner movement
does not meet the strict closing-loaded majority rule. It demonstrates that
coarse observation spacing can produce a progression that resembles a burst
without satisfying a single timing archetype for both vectors.

### 5.3 Round 342,151: deployment and miner timing separate

The median-count current-round example from Discovery Session 2 records its
largest miner-count movement near the opening and its largest deployment
movement late. It satisfies the broad single-transition deployment threshold
but not the corresponding miner threshold. It is a counterexample to treating
deployment and miner concentration as one interchangeable property.

### 5.4 Rounds outside the diagnostic motifs

There are 3,847 complete rounds that satisfy none of the four broad timing/
burst probes. This population prevents those probes from functioning as an
exhaustive classification even before questions of threshold sensitivity are
considered.

### 5.5 Capture-regime counterexample

Exact synchronization appears in 2,130 of 2,188 large-gap rounds but only 166
of 15,724 rounds without a large gap. This contrast shows that a seemingly
strong behavioral separation can align with observation density. It cannot be
accepted as an intrinsic round class from this archive alone.

## 6. Confidence assessment

| Claim | Confidence | Basis |
|---|---|---|
| Multiple recurring behavioral motifs exist | High | Thousands of rounds repeatedly satisfy explicit movement and leadership descriptions |
| Initialization-dominated bursts recur | High | 4,113 strict matches; strong association with an exact zero initial state |
| Distributed movement recurs | High | 8,307 strict four-quarter matches across the archive chronology |
| Stable leader with changing lower order recurs | High | 2,342 deployment matches and 1,219 miner matches |
| Closing-loaded movement recurs | Moderate | 129 matches across chronology, but substantial overlap with other motifs |
| A distinct long-quiet-suffix class exists | Very low | Only one round has a quiet suffix of at least half its duration |
| Exact synchronization defines a natural class | Very low | Exact synchronization is tightly associated with large observation gaps |
| The archive supports discrete, mutually exclusive natural classes | Low | Smooth metric ranges, 3,900 multi-motif matches, 3,847 nonmatches, and capture-regime associations |

### Observation

The complete-round population displays repeatable differences in movement
timing, burst concentration, order stability, leader stability, quiet periods,
observation density, and deployment/miner synchronization.

### Inference

Those differences are best described as overlapping behavioral dimensions and
recurring motifs. The archive does not presently justify believing that all
rounds naturally separate into a small set of discrete classes.

### Speculation

No claim is made about causes, latent mechanisms, predictive value, or how any
future taxonomy should be constructed.

## 7. New questions raised

- Do the observed movement-concentration ranges retain their shapes when rounds
  are compared only within one observation-density regime?
- How much of the initialization-dominated motif remains when lifecycle start
  state is held constant?
- Do deployment and miner movement continue to show different dominant-quarter
  patterns under uniformly spaced observations?
- Is stable leadership with changing lower order equally frequent across the
  retained observation chronology?
- How sensitive are the descriptive motif counts to fixed thresholds such as
  one-half movement concentration?
- Which behaviors remain recurring when motifs are described without elapsed-
  time quarters?
- Are the 3,847 nonmatching rounds continuously distributed between the broad
  motifs or do they share another directly observable property?
- Does the association between exact synchronization and large observation
  gaps persist in a dataset with uniform observation cadence?
