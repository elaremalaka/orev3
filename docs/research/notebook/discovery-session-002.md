# Discovery Session 2 — Round Evolution

## Status

Read-only exploratory description of the archived RFC-012 research dataset.
This session does not perform predictive modeling, propose strategies, or
create formal Research Questions.

## 1. Objective

This session describes how a small, objectively selected set of ORE rounds
changes across its complete recorded observation sequence. It focuses on:

- deployed lamports by square;
- miner counts by square;
- changes in the complete 25-square ordering;
- deployment and miner leadership;
- the timing of visible movement; and
- intervals in which neither vector changes.

The source is the cumulative archived dataset documented in
[Discovery Session 1](discovery-session-001.md). Full snapshots are resolved
from each replay round's ordered raw observation references. Outcome fields are
used only to classify the requested provenance contrasts; they are not used to
describe or select decision-time movements.

This is descriptive observation only. Counts and arithmetic differences report
what appears in the selected records and do not test relationships or explain
causes.

## 2. Round selection methodology

### 2.1 Eligible population

Selection used the 17,912 replay rounds whose lifecycle coverage status is
`complete`. This avoids making incomplete boundary coverage the common reason
for differences among the three examples.

The complete-round observation-count range is 14–146 and its median is 78.
Three deterministic rules were applied in order:

1. **Round A:** among complete replay rounds with a locally observed
   `current_round` outcome, select the observation count nearest the complete-
   round median; break ties by the lowest `round_id`.
2. **Round B:** among the remaining complete replay rounds, select the highest
   observation count; break ties by the lowest `round_id`.
3. **Round C:** among the remaining complete replay rounds with a locally
   observed `post_transition_predecessor` outcome, select the lowest observation
   count; break ties by the lowest `round_id`.

The resulting selection is:

| Label | Round | Objective contrast | Observations | Recorded duration | Outcome provenance |
|---|---:|---|---:|---:|---|
| A | 342,151 | Median-count current-round example | 78 | 77.582 s | `observed` / `current_round` |
| B | 343,458 | Archive-wide maximum count among complete rounds | 146 | 146.051 s | Missing |
| C | 362,945 | Minimum-count post-transition example | 14 | 70.311 s | `observed` / `post_transition_predecessor` |

Round B's missing outcome is an additional objective contrast: complete replay
coverage and outcome availability are separate properties. No round was chosen
because its trajectory appeared representative or interesting.

### 2.2 Descriptive method

For each round:

- snapshots remain in canonical timestamp, source-file, and source-line order;
- square identifiers below are one-based (`1`–`25`);
- total deployed lamports is the sum of the 25-square deployment vector;
- square miner count is the sum of the 25 per-square counts and is reported
  separately from the protocol's `total_miners` field;
- square ordering sorts values descending, with square identifier resolving
  equal-value presentation order;
- a leader state retains every square tied for the maximum;
- an ordering change means the complete 25-square ordering differs from the
  preceding observation; and
- movement is the sum of absolute per-square changes between consecutive
  observations.

Each lifecycle is shown at five fixed observation-position checkpoints and then
described through the actual change events between them. Checkpoints are a
display aid; all observations were inspected for movement, order changes,
leadership changes, and quiet intervals.

## 3. Round A — 342,151

### 3.1 Lifecycle summary

| Property | Value |
|---|---|
| Observations | 78 |
| Time span | `2026-07-23T06:42:02.883879Z`–`2026-07-23T06:43:20.465408Z` |
| Duration | 77.582 seconds |
| RPC-slot span | 434,665,507–434,665,694 |
| Coverage | `complete` |
| Outcome capture | `observed` / `current_round` |

### 3.2 Progression checkpoints

| Observation | Elapsed | Total deployed | Sum of square miner counts | Deployment top five | Miner-count top five | Leaders: deployment / miners |
|---:|---:|---:|---:|---|---|---|
| 1 | 0.000 s | 6,510,142,759 | 3,264 | 25, 21, 23, 24, 22 | 25, 21, 23, 3, 7 | 25 / 25 |
| 20 | 19.117 s | 6,623,674,109 | 3,487 | 25, 21, 23, 24, 22 | 25, 23, 11, 21, 3 | 25 / 25 |
| 39 | 38.282 s | 6,652,667,359 | 3,521 | 25, 21, 23, 24, 22 | 25, 11, 23, 3, 21 | 25 / 25 |
| 59 | 58.443 s | 9,740,678,257 | 3,786 | 21, 23, 24, 25, 10 | 3, 7, 25, 13, 23 | 21 / 3, 7, 25 tie |
| 78 | 77.582 s | 10,036,160,792 | 3,888 | 21, 23, 24, 25, 22 | 7, 3, 11, 13, 25 | 21 / 7 |

### 3.3 Evolution by phase

#### Opening: observations 1–20, 0.000–19.117 seconds

Total deployment increases by 113,531,350 lamports and the sum of square miner
counts increases by 223. The deployment ordering changes once; the miner-count
ordering changes four times. Square 25 remains the sole leader of both vectors.

Miner-count movement is visible in the first seconds: the largest miner-count
change in the whole round is 75 counts at observation 5, 4.028 seconds after
the first observation. The deployment vector does not undergo its largest
change at that time.

#### Quiet middle: observations 20–39, 19.117–38.282 seconds

This interval adds 28,993,250 deployed lamports and 34 square miner counts. The
deployment ordering does not change and the miner-count ordering changes once.
Both leaders remain square 25.

The longest interval with neither vector changing runs from observation 16 to
33, covering 15.100–32.225 elapsed seconds, or 17.125 seconds. It crosses the
first and second display phases.

#### Main movement: observations 39–59, 38.282–58.443 seconds

This interval contains the largest visible movement: 3,088,010,898 additional
deployed lamports and 265 additional square miner counts. Deployment ordering
changes four times and miner-count ordering changes six times.

Deployment leadership changes once, from square 25 to square 21 at observation
44 (43.315 seconds), and square 21 remains the deployment leader thereafter.
The largest single deployment change is 1,812,615,719 lamports at observation
54 (53.393 seconds). Further changes of 452,399,994, 367,238,372, and
330,989,538 lamports appear at observations 56–58, from 55.413 to 57.433
seconds.

At observation 58 the miner lead changes from square 25 to a three-way tie
among squares 3, 7, and 25.

#### Closing: observations 59–78, 58.443–77.582 seconds

This interval adds 295,482,535 deployed lamports and 102 square miner counts.
Deployment ordering changes twice, but square 21 retains the lead. Miner-count
ordering changes three times: the three-way lead narrows to squares 7 and 25 at
59.448 seconds and then to square 7 alone at 60.458 seconds. Square 7 remains
the miner-count leader through the final observation.

Across the full lifecycle, deployment ordering changes on 7 of the 77
observation transitions and miner-count ordering changes on 14. Deployment has
two leader states (25, then 21); miner counts have four leader states, including
two ties. Every recorded per-square movement in this round is nondecreasing.

## 4. Round B — 343,458

### 4.1 Lifecycle summary

| Property | Value |
|---|---|
| Observations | 146 |
| Time span | `2026-07-24T11:05:28.277206Z`–`2026-07-24T11:07:54.328214Z` |
| Duration | 146.051 seconds |
| RPC-slot span | 434,909,216–434,909,566 |
| Coverage | `complete` |
| Outcome | Missing |

### 4.2 Progression checkpoints

| Observation | Elapsed | Total deployed | Sum of square miner counts | Deployment top five | Miner-count top five | Leaders: deployment / miners |
|---:|---:|---:|---:|---|---|---|
| 1 | 0.000 s | 0 | 0 | all squares tied | all squares tied | all / all |
| 37 | 36.239 s | 4,788,248,737 | 3,406 | 13, 21, 25, 22, 23 | 12, 3, 13, 1, 11 | 13 / 12 |
| 73 | 72.487 s | 7,542,464,276 | 3,832 | 13, 23, 11, 1, 22 | 12, 1, 3, 18, 11 | 13 / 12 |
| 110 | 109.766 s | 7,542,464,276 | 3,832 | 13, 23, 11, 1, 22 | 12, 1, 3, 18, 11 | 13 / 12 |
| 146 | 146.051 s | 7,542,464,276 | 3,832 | 13, 23, 11, 1, 22 | 12, 1, 3, 18, 11 | 13 / 12 |

### 4.3 Evolution by phase

#### Initialization burst: observations 1–6, 0.000–5.036 seconds

The first two observations have zero deployed lamports and zero square miner
counts, so all squares are tied. The first nonzero changes appear at observation
3, after 2.014 seconds.

Deployment leadership passes through an incomplete tie at observation 3,
square 6 at observation 4, square 19 at observation 5, and square 13 at
observation 6. Miner leadership changes from the all-square tie to square 12,
then a seven-square tie, then a square 12/19 tie, and back to square 12 alone at
observation 6.

The largest changes in the round end at observation 6: 3,857,454,312 deployed
lamports and 2,330 square miner counts are added between observations 5 and 6.
From that point, square 13 remains the deployment leader for the remaining 141
observations.

#### Continued movement: observations 6–37, 5.036–36.239 seconds

By observation 37, total deployment is 4,788,248,737 lamports and the square
miner-count sum is 3,406. Deployment and miner rankings continue to change even
though their sole leaders remain squares 13 and 12. Across observations 1–37,
the complete deployment ordering changes seven times and the miner ordering
changes ten times.

#### Secondary movement: observations 37–73, 36.239–72.487 seconds

This phase adds 2,754,215,539 deployed lamports and 426 square miner counts.
Deployment ordering changes six times; miner ordering changes seven times.

The deployment changes include 253,400,000 lamports at 52.344 seconds,
1,112,088,079 at 55.356 seconds, 250,000,000 at 58.382 seconds, and
635,901,081 at 61.397 seconds. Miner leadership briefly becomes a tie between
squares 3 and 12 at observation 48 (47.303 seconds), then returns to square 12
alone at observation 62 (61.397 seconds).

The final full-order changes for both vectors occur at observation 64, 63.411
seconds after the first observation.

#### Quiet suffix: observations 64–146, 63.411–146.051 seconds

Neither deployed lamports nor miner counts change over this 82.640-second
interval. The top-five orders and sole leaders remain square 13 for deployment
and square 12 for miner count. The final two fixed checkpoint intervals contain
zero vector movement and zero ranking changes.

Across the full lifecycle, deployment ordering changes on 13 transitions and
miner ordering on 17. Four deployment-leader changes occur, all during the
opening five seconds. Six miner-leader changes occur, with the last at 61.397
seconds. Every recorded per-square movement in this round is nondecreasing.

## 5. Round C — 362,945

### 5.1 Lifecycle summary

| Property | Value |
|---|---|
| Observations | 14 |
| Time span | `2026-08-11T04:36:45.263018Z`–`2026-08-11T04:37:55.573850Z` |
| Duration | 70.311 seconds |
| RPC-slot span | 438,539,225–438,539,391 |
| Coverage | `complete` |
| Outcome capture | `observed` / `post_transition_predecessor` |

### 5.2 Progression checkpoints

| Observation | Elapsed | Total deployed | Sum of square miner counts | Deployment top five | Miner-count top five | Leaders: deployment / miners |
|---:|---:|---:|---:|---|---|---|
| 1 | 0.000 s | 18,825,110,305 | 2,915 | 13, 11, 21, 22, 18 | 2, 13, 1, 4, 18 | 13 / 2, 13 tie |
| 4 | 50.299 s | 19,060,110,255 | 3,059 | 22, 13, 18, 2, 4 | 2, 13, 4, 18, 1 | 22 / 2, 13 tie |
| 7 | 53.326 s | 19,968,558,049 | 3,142 | 4, 11, 21, 2, 3 | 1, 2, 4, 13, 3 | 4 / 1, 2, 4 tie |
| 11 | 67.293 s | 19,978,558,049 | 3,167 | 4, 11, 21, 2, 3 | 1, 2, 4, 13, 3 | 4 / 1, 2, 4 tie |
| 14 | 70.311 s | 19,978,558,049 | 3,167 | 4, 11, 21, 2, 3 | 1, 2, 4, 13, 3 | 4 / 1, 2, 4 tie |

### 5.3 Evolution by phase

#### Sparse opening: observations 1–2, 0.000–48.279 seconds

The lifecycle begins with square 13 leading deployment and squares 2 and 13
tied for the miner-count lead. The second observation arrives 48.279 seconds
later. At that point deployment has increased by 234,999,950 lamports and the
square miner-count sum by 144. The deployment leader changes to square 22; the
miner leaders remain squares 2 and 13.

#### Concentrated change: observations 2–7, 48.279–53.326 seconds

Observations 3–6 do not change the vectors. At observation 7, 53.326 seconds
after the start, deployment increases by 908,447,794 lamports and square miner
counts by 83. The full ordering of each vector changes for the second and final
time.

Deployment leadership changes from square 22 to square 4. Miner leadership
changes from the square 2/13 tie to a three-way tie among squares 1, 2, and 4.
Both leader states remain unchanged through the end.

#### Late small update: observations 7–11, 53.326–67.293 seconds

The longest fully quiet interval runs from observation 7 to 8, covering 10.950
seconds. At observation 9 (65.285 seconds), deployment increases by 10,000,000
lamports and the square miner-count sum by 25. Neither complete ordering nor
either leader state changes.

#### Final stability: observations 11–14, 67.293–70.311 seconds

Neither vector changes. The final deployment top five remains 4, 11, 21, 2,
and 3; the final miner-count top five remains 1, 2, 4, 13, and 3.

Across the 13 observation transitions, each complete ordering changes twice.
Deployment leadership changes twice; miner leadership changes once. Every
recorded per-square movement in this round is nondecreasing.

## 6. Cross-round observations

### 6.1 Movement timing

- Round A records modest opening movement, a 17.125-second interval with no
  vector change, its largest deployment movement at 53.393 seconds, and further
  smaller movement through the closing phase.
- Round B records its largest movement during the opening 5.036 seconds,
  secondary movement through 63.411 seconds, and then an 82.640-second fully
  quiet suffix.
- Round C has a 48.279-second gap between its first two observations. Its two
  ordering changes occur at 48.279 and 53.326 seconds, followed by one smaller
  update at 65.285 seconds.

Movement is therefore not confined to the same relative phase in these three
records.

### 6.2 Ranking and leader stability

- Round A's deployment leader changes once and stabilizes earlier than its
  miner-count leader. Full rankings continue to change after deployment
  leadership settles.
- Round B's deployment leader stabilizes after 5.036 seconds, although its full
  deployment ordering continues to change until 63.411 seconds. Miner
  leadership changes later than deployment leadership.
- Round C's two deployment-leader changes and one miner-leader change coincide
  with its two order-changing observations. Both final leader states begin at
  53.326 seconds.

Leadership stability and full-order stability are distinct in all three
descriptions: a leader can remain fixed while lower ranks continue changing.

### 6.3 Deployment and miner movement

- Both vectors move during the principal bursts in all three rounds.
- They do not preserve the same ordering. Final deployment/miner leaders are
  21/7 in Round A, 13/12 in Round B, and 4/(1, 2, 4 tie) in Round C.
- Round A's largest miner-count movement appears near the beginning, while its
  largest deployment movement appears late.
- Round B's largest deployment and miner-count changes end at the same opening
  observation.
- Round C's three nonzero deployment updates occur at the same observations as
  its three nonzero miner-count updates.

### 6.4 Quiet periods and observation count

- Every selected round contains at least one interval in which neither vector
  changes.
- Round B has the most observations and the longest fully quiet interval; more
  than half of its recorded duration follows its final vector change.
- Round C has the fewest observations but a duration close to Round A because
  its first observation gap is 48.279 seconds.
- Complete coverage status does not imply uniform observation spacing or
  continuous vector movement.

## 7. Surprises

The following are descriptive contrasts that were not apparent from lifecycle
counts alone:

- The maximum-observation example spends its last 82.640 seconds with identical
  deployment and miner-count vectors.
- The minimum-observation complete example covers 70.311 seconds because a
  48.279-second gap separates its first two observations.
- Deployment leadership can stabilize long before the complete deployment
  order stops changing, as in Round B.
- Miner-count and deployment leaders differ at the final observation of all
  three rounds.
- Ties are part of the visible leadership history: all-square initialization
  ties, temporary multi-square ties, and a final three-square miner tie all
  occur in the selected records.
- The timing relationship between miner-count and deployment movement is not
  uniform across the three rounds: it separates in Round A, aligns at the
  largest opening event in Round B, and aligns at every nonzero update in Round
  C.

## 8. Questions raised

- Across the full archive, how often is visible movement concentrated near the
  opening, middle, or closing portion of a round?
- How often does a round end with different deployment and miner-count leaders?
- How often does leader stability precede complete-order stability?
- How common are long fully quiet suffixes after the final vector change?
- How does observation spacing affect the number of distinct movements visible
  in a complete lifecycle?
- How often do deployment and miner-count changes occur in the same observation
  transition?
- How frequently do ties occur in deployment leadership and miner-count
  leadership over a round's recorded history?
- How often does a high observation count represent continued movement versus
  repeated unchanged snapshots?
