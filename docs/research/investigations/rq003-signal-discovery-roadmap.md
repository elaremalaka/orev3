# RQ-003 Signal Discovery Roadmap

## Status and scope

- Type: Research planning
- Implementation authorized: No
- Derived-measurement approval granted: No
- Experiment protocol authorized: No

This roadmap identifies scientifically distinct candidate signals for future
outcome-blind characterization. It does not define a production measurement,
Feature Set, ranking procedure, experiment protocol, model, Strategy, or
economic interpretation.

The roadmap uses only:

- [RQ-003](../questions/RQ-003-winning-square-predictability.md);
- the [RQ-003 Measurement Catalog](rq003-measurement-catalog.md);
- the [Feature Eligibility Resolution](../questions/RQ-003-feature-eligibility-resolution.md);
- the [Feature Set 1 Design](rq003-feature-set-1-design.md);
- [Finding 001](../findings/rq003-experiment-001-analysis.md); and
- [Finding 002](../findings/rq003-experiment-002-analysis.md).

All formulas below are conceptual mathematical definitions for roadmap
comparison only. They remain unapproved until a separate design and protocol
fixes exact arithmetic, zero handling, identities, revision scope, and
conformance rules.

## 1. Completed scientific foundation

The eight approved fundamental measurements are:

1. per-square deployed lamports `D_s`;
2. per-square miner counts `M_s`;
3. round-wide unique-authority count `T_M`;
4. Board production-cost EMA `C`;
5. Active-Round motherlode `R_L`;
6. Treasury motherlode `T_L`;
7. pre-finalization total vaulted `V`; and
8. legacy pre-finalization total winnings `W` within its defining revision.

The two completed findings constrain the roadmap without establishing
predictive value for any new candidate:

- Finding 001 reports negative evidence for direct descending `D_s` ordering.
  Any positive scaling, share, rank, or other order-preserving transformation
  of `D_s` therefore repeats the same ordering question rather than creating a
  new signal.
- Finding 002 reports that `D_s / M_s` materially changes ordering relative to
  `D_s`. It does not evaluate winner prediction. A transformation that differs
  only by a positive round-wide scaling or shift of `D_s / M_s` is not a new
  signal.

The next phase should therefore emphasize candidate-varying relationships that
can generate orderings distinct from both `D_s` and `D_s / M_s`.

## 2. Eligibility and prioritization rules

Every roadmap candidate must:

- use only the frozen decision-time values of the eight approved fundamental
  measurements;
- remain deterministic, immutable, finite, and outcome-blind;
- avoid protocol revision, chronology, cadence, lifecycle coverage, identity,
  and missingness as signal inputs;
- preserve the distinction between per-square memberships and round-wide
  unique miners;
- avoid finalized-value substitution and cross-account repair;
- declare exact zero, tie, unit, and revision semantics before implementation;
- measure an observable relationship rather than classify, score, recommend,
  or predict; and
- derive directly from fundamental measurements rather than another
  registered derived output.

Priority uses only:

1. scientific novelty;
2. independence from Finding 001 and Finding 002; and
3. likelihood of producing materially different candidate orderings.

Expected mining profitability is not considered.

## 3. Mathematical screening

Several intuitive transformations are not new ordering signals and should not
receive characterization experiments of their own.

| Screened transformation | Mathematical result | Roadmap disposition |
| --- | --- | --- |
| Deployment share `D_s / ΣD` | The denominator is common and positive within a decision, so ordering is identical to `D_s`. | Exclude; Finding 001 already answers the direct-ordering question. |
| Deployment rank or percentile | Monotonic representation of `D_s`; ties aside, ordering is unchanged. | Exclude as an independent signal. |
| Miner share `M_s / ΣM` | The denominator is common within a decision, so ordering is identical to `M_s`. | Use only as an interpretable component of a cross-measurement relationship. |
| Miner rank or percentile | Monotonic representation of `M_s`. | Not an independent signal; useful only inside a multi-measurement relationship. |
| `D_s / C` or `D_s / T_L` | Division by one positive round-wide scalar preserves deployment ordering. | Exclude as standalone candidate rankings. |
| `M_s / T_M` | Division by one positive round-wide scalar preserves miner-count ordering. | Exclude as a standalone candidate ranking. |
| `(D_s / M_s) / C` or `T_M(D_s / M_s)` | A common positive round-wide factor preserves the Finding 002 ordering. | Exclude as a new signal. |
| Centered deployment `D_s - reference` | Subtracting one round-wide constant preserves deployment ordering. | Exclude unless the reference is multiplied by a candidate-varying quantity. |
| Active-Round/Treasury motherlode gap under the supported revision | The active pre-finalization field is initialized to zero, so the gap collapses to the Treasury value. | No independent signal in the current revision. |
| Any finalized aggregate or later motherlode value | Crosses the RQ-003 outcome boundary. | Prohibited. |
| Observation-index deltas or rolling windows | Eligibility remains deferred because they mix protocol movement with collection cadence. | Outside this roadmap until the existing eligibility question is resolved. |

This screening is algebraic, not empirical. It avoids spending future
experiments on transformations whose ordering is already determined.

### Archival correction — zero-valued `V` and `W`

This correction was added during historical repository restoration. The
original roadmap grouped `D_s / V` with positive-scalar normalizations and
later retained `V / T_M` and legacy `W`–`V` relationships as low-priority
context candidates. Contemporaneous
[Experiment 0B](../notebook/experiment-000-characterization.md) evidence had
already established that both `V` and `W` were constant zero throughout the
governed replay population. Consequently:

- `D_s / V` was undefined in that population and was not an order-preserving
  positive-scalar normalization;
- `V / T_M` was constant zero and could not distinguish observed regimes; and
- any `W`–`V` relationship was degenerate for the observed population, with a
  ratio using `V` as denominator undefined.

The Section 6.3 and 6.4 entries and their Section 8 summary rows are retained
as historical candidate ideas, but they were non-actionable for the governed
population. This correction does not change the historical participant-state
research ordering or any roadmap priority. It uses no later Experiment 2C,
2D, 3, or 4 result, and no new scientific analysis was performed.

## 4. High-priority candidates

### 4.1 Signed deployment–miner share imbalance

**Inputs:** `D_s`, all 25 deployed values, `M_s`, and all 25 per-square miner
counts.

**Conceptual quantity:**

```text
I_s = D_s / ΣD - M_s / ΣM
```

An exact implementation could compare the signed numerator
`D_s(ΣM) - M_s(ΣD)` while preserving the declared rational semantics.

**Scientific motivation:** This measures whether one square carries a larger
share of deployment than its share of observed per-square miner membership.
It is a contemporaneous participant-state relationship, not an economic
efficiency claim.

**Why mathematically distinct:** It is not a monotonic transformation of
`D_s`, `M_s`, or `D_s / M_s`. The `M_s`-weighted subtraction permits two
squares to reverse even when their raw deployment and deployment-per-miner
orders agree.

**Why it could contain different information:** It represents directional
disagreement between two complete board distributions. Finding 001 considered
deployment alone; Finding 002 considered a local ratio. Neither considered
the difference between each square's shares of the two board totals.

**Expected characterization complexity:** Moderate. It requires exact rational
or cross-product arithmetic, explicit zero-total invalidity, signed ordering,
and proof that `ΣM` means per-square membership total rather than `T_M`.

**Expected predictive-evaluation priority:** Highest among the derived
candidates, after outcome-blind characterization proves ordering novelty.

### 4.2 Joint deployment–miner intensity

**Inputs:** `D_s` and `M_s`.

**Conceptual quantity:**

```text
J_s = D_s × M_s
```

**Scientific motivation:** This measures the joint magnitude of deployed
lamports and recorded miner membership on one square. It is the complementary
relationship to Deployment per Miner: rather than increasing when deployment
is large relative to participation, it increases when both quantities are
large together.

**Why mathematically distinct:** A product is not monotonic in either input
when both vary across squares. It can reverse raw-deployment, miner-count, and
deployment-per-miner orderings.

**Why it could contain different information:** It measures co-concentration
of the two participant-state quantities. Neither completed finding tested a
joint-magnitude ordering.

**Expected characterization complexity:** Low to moderate. Arithmetic is exact
integer multiplication, but bounds, canonical encoding, and product-range
validation must be declared.

**Expected predictive-evaluation priority:** High because it is simple,
independent of the two completed orderings, and likely to produce strict
reordering whenever deployment and miner-count order disagree.

### 4.3 Deployment–miner rank consensus

**Inputs:** the complete `D_s` and `M_s` vectors.

**Conceptual quantity:** the arithmetic mean, or equivalently the sum, of one
square's average deployment rank and average miner-count rank. Lower consensus
rank indicates stronger joint placement.

**Scientific motivation:** This measures agreement in relative board position
without allowing one measurement's raw magnitude scale to dominate the other.

**Why mathematically distinct:** Combining two rank vectors can order squares
differently from either source vector and from `D_s / M_s`. It is not a
monotonic transformation of any one evaluated signal.

**Why it could contain different information:** It preserves only relative
position in each participant-state distribution. That makes it scientifically
distinct from both the magnitude-sensitive product and the exact local ratio.

**Expected characterization complexity:** Moderate. Average-rank ties must be
exact, candidate identity may not break ties, and the orientation of the
combined value must be explicit.

**Expected predictive-evaluation priority:** High, following signed share
imbalance, because it provides a magnitude-insensitive test of joint
participant-state ordering.

## 5. Medium-priority candidates

### 5.1 Signed deployment–miner rank gap

**Inputs:** the complete `D_s` and `M_s` vectors.

**Conceptual quantity:**

```text
G_s = rank_M(s) - rank_D(s)
```

with exact average ranks for ties and a predeclared sign convention.

**Scientific motivation:** This measures how far deployment position leads or
lags miner-count position for one square.

**Why mathematically distinct:** Rank subtraction is not monotonic in either
source ranking. It also discards the magnitude information used by
Deployment per Miner and signed share imbalance.

**Why it could contain different information:** It isolates relative-position
disagreement rather than level, ratio, or joint intensity.

**Expected characterization complexity:** Moderate. The experiment must report
ties, signed and absolute gap distributions, and algebraic overlap with rank
consensus.

**Expected predictive-evaluation priority:** Medium. It is scientifically
distinct, but it is adjacent to the higher-priority share-imbalance and rank-
consensus families.

### 5.2 Absolute deployment–miner share imbalance

**Inputs:** the same fundamental vectors as signed share imbalance.

**Conceptual quantity:**

```text
A_s = |D_s / ΣD - M_s / ΣM|
```

**Scientific motivation:** This measures the magnitude of disagreement between
deployment share and membership share without asserting that deployment-heavy
or miner-heavy disagreement is preferable.

**Why mathematically distinct:** Absolute value is non-monotonic over the
signed imbalance and can place large deviations from either direction ahead
of balanced squares. It is not order-equivalent to `D_s` or `D_s / M_s`.

**Why it could contain different information:** It tests whether discrepancy
magnitude is a distinct observable concept from discrepancy direction.

**Expected characterization complexity:** Moderate. It should be characterized
only after the signed form so that loss of direction and any ordering overlap
are explicit.

**Expected predictive-evaluation priority:** Medium to low within this group.
Its novelty is real, but it discards information retained by the signed form.

### 5.3 Per-square deployment–miner discordance burden

**Inputs:** complete `D_s` and `M_s` vectors.

**Conceptual quantity:** for each square, count the other squares for which its
pairwise deployment relation and pairwise miner-count relation disagree.

**Scientific motivation:** Finding 002 reports board-wide pairwise divergence.
This candidate attributes contemporaneous cross-measurement disagreement to
individual squares without using outcomes.

**Why mathematically distinct:** An incident discordance count records the
number of conflicting pairwise relations, not their net rank displacement.
Two squares can have the same rank gap but different discordance burdens.

**Why it could contain different information:** It measures local structural
instability between the two participant orderings rather than magnitude or
direction alone.

**Expected characterization complexity:** High. It requires deterministic
pairwise tie semantics, `25 × 24` relation accounting, exact symmetry checks,
and proof that the per-square totals reconcile with board-wide discordance.

**Expected predictive-evaluation priority:** Medium. Finding 002 makes
variation plausible, but the candidate is more complex and should follow the
simpler relationship measurements.

### 5.4 Production-cost-adjusted deployment margin

**Inputs:** `D_s`, `M_s`, and Board production-cost EMA `C`.

**Conceptual quantity, conditional on compatible units:**

```text
K_s = D_s - C × M_s
```

**Scientific motivation:** This would relate participant-state deployment to
the protocol-maintained, lagged production-cost scale at the same frozen
observation.

**Why mathematically distinct:** When the candidate-varying miner count
multiplies the shared Board quantity, the result need not preserve deployment,
miner-count, or Deployment-per-Miner ordering.

**Why it could contain different information:** It would test whether the
cross-account cost scale changes how deployment and participation should be
measured together, without calculating the EMA or reading supplementary state.

**Expected characterization complexity:** High. Before any formula is
approved, a semantic review must prove compatible units, multiplication
meaning, zero and missing behavior, lag interpretation, and revision scope.
The roadmap does not assume that proof will succeed.

**Expected predictive-evaluation priority:** Medium only after semantic
eligibility is proven. Until then it is blocked from implementation and ranks
below all participant-only candidates.

## 6. Low-priority context candidates

These candidates are mathematically distinct round-level measurements, but a
single value repeated for all 25 squares cannot produce a candidate ordering
on its own. Their scientific role would be outcome-blind regime
characterization before any future, separately governed multi-measurement
Feature Set considers an interaction.

### 6.1 Per-round participation multiplicity

**Inputs:** `ΣM` and `T_M`.

**Conceptual quantity:** the ratio of summed per-square miner memberships to
the protocol-published unique round-wide miner count.

**Scientific motivation:** This measures how per-square authority memberships
relate to unique round participation while preserving the catalog's rule that
the two quantities are not equal.

**Why mathematically distinct:** Neither input reconstructs the other, and the
ratio is not a transformation of raw deployment or Deployment per Miner.

**Why it could contain different information:** It describes participation
breadth across the board, a concept absent from Findings 001 and 002.

**Expected characterization complexity:** Moderate, including denominator
validation and explicit prohibition on interpreting authorities as people,
machines, or transactions.

**Expected predictive-evaluation priority:** Low. It cannot order squares
without a future candidate-varying interaction.

### 6.2 Treasury motherlode per unique miner

**Inputs:** Treasury motherlode `T_L` and round-wide unique-authority count
`T_M`.

**Conceptual quantity:** `T_L / T_M`, with explicit zero-denominator rules.

**Scientific motivation:** This measures the contemporaneous scale of the live
Treasury pool relative to unique round participation. It is not a payout,
expected reward, or per-participant entitlement.

**Why mathematically distinct:** It is a cross-account round-level relationship
and is not a transformation of either evaluated per-square ordering.

**Why it could contain different information:** It may distinguish Treasury
and participation regimes absent from participant vectors alone.

**Expected characterization complexity:** High because cross-account context,
denomination, denominator semantics, and revision identity must remain
explicit. No supplementary read or repair is permitted.

**Expected predictive-evaluation priority:** Low. It supplies no standalone
candidate ordering and should not advance without a separately justified
candidate-varying interaction.

### 6.3 Pre-finalization vaulted amount per unique miner

**Inputs:** pre-finalization total vaulted `V` and round-wide unique-authority
count `T_M`.

**Conceptual quantity:** `V / T_M`, with explicit zero-denominator rules.

**Scientific motivation:** This measures the frozen round-wide vaulted scale
relative to unique participation. It does not attribute vault contents to an
individual authority or imply return, settlement, or efficiency.

**Why mathematically distinct:** It relates two independent Round aggregates
and does not transform either previously evaluated candidate ordering.

**Why it could contain different information:** It may distinguish
participant-state scale regimes not represented by per-square vectors alone.

**Expected characterization complexity:** Moderate to high. The exact
pre-finalization provenance, denominations, denominator semantics, and
revision scope must be proven.

**Expected predictive-evaluation priority:** Low because the value is common
to all candidates in one decision.

### 6.4 Legacy winnings-to-vaulted relationship

**Inputs:** legacy pre-finalization `W` and `V` within the exact revision that
defines both meanings.

**Scientific motivation:** This could characterize the contemporaneous
relationship between two legacy Round aggregates without substituting a
finalized or successor field.

**Why mathematically distinct:** It is a revision-scoped aggregate
relationship, not a monotonic transformation of either evaluated per-square
signal.

**Why it could contain different information:** It may distinguish legacy
pre-finalization Round-state regimes.

**Expected characterization complexity:** High. Semantic compatibility,
denomination, zero handling, and strict exclusion of successor
`total_returned_sol` are mandatory.

**Expected predictive-evaluation priority:** Lowest. It is revision-limited,
round-global, and incapable of ordering candidates without a separately
governed interaction.

## 7. Measurements not advanced by this roadmap

The following do not currently justify new signal experiments:

- **Active-Round motherlode derivations:** the approved decision-time value is
  initialized to zero under the supported revision. Relationships that merely
  subtract it from another scalar collapse to the other scalar, while a
  nonzero finalized value is prohibited outcome information.
- **Simple Board/Treasury normalization:** multiplying or dividing every
  candidate by one positive round-wide scalar preserves its existing ordering.
- **Arbitrary nonlinear powers or smoothing constants:** expressions such as
  `D_s / M_s²` or `D_s / (M_s + constant)` can force new orderings but lack an
  independently motivated observable meaning.
- **Topology-derived measurements:** the available authority does not define a
  scientific neighborhood topology for the 25 ordered squares. A topology
  should not be invented to manufacture locality.
- **Historical movement measurements:** cadence-sensitive differences,
  rolling windows, and leader persistence remain deferred by the Feature
  Eligibility Resolution.
- **Reward-derived measurements:** candidate-square semantics remain deferred.
- **Absolute timing and observation availability:** these classes are rejected
  as chronology or collector-regime signals.

## 8. Prioritized candidate summary

| Priority | Candidate | Scientific novelty | Independence from prior findings | Likelihood of materially different ordering | Characterization complexity | Predictive-evaluation priority |
| --- | --- | --- | --- | --- | --- | --- |
| High | Signed deployment–miner share imbalance | Directional disagreement between complete participant distributions | Distinct from raw deployment and local Deployment per Miner | High | Moderate | 1 |
| High | Joint deployment–miner intensity | Joint magnitude and co-concentration | Tests the opposite relationship direction from division | High | Low–moderate | 2 |
| High | Deployment–miner rank consensus | Magnitude-insensitive joint relative position | Neither completed finding combined both rank vectors | High | Moderate | 3 |
| Medium | Signed deployment–miner rank gap | Relative-position disagreement | Distinct from magnitude and ratio signals | Moderate–high | Moderate | 4 |
| Medium | Absolute share imbalance | Direction-free distribution disagreement | Non-monotonic relative to signed imbalance and prior signals | Moderate–high | Moderate | 6 |
| Medium | Per-square discordance burden | Candidate-local pairwise ordering conflict | Extends Finding 002's board summary without using outcomes | Moderate–high | High | 5 |
| Medium, conditional | Production-cost-adjusted deployment margin | Participant/protocol-state relationship | Adds a lagged Board quantity absent from prior findings | Potentially high, but unproven | High | 7 after semantic proof |
| Low | Per-round participation multiplicity | Unique-authority versus membership breadth | New round-global participant context | None alone | Moderate | Context only |
| Low | Treasury motherlode per unique miner | Treasury/participation scale | New round-global context | None alone | High | Context only |
| Low | Pre-finalization vaulted amount per unique miner | Vaulted/participation scale | New round-global context | None alone | Moderate–high | Context only |
| Low | Legacy winnings-to-vaulted relationship | Revision-scoped aggregate regime | New legacy-only context | None alone | High | Context only |

The numeric ordering in the final column sequences future predictive
consideration only. It does not authorize outcome evaluation, and every
candidate must first complete mathematical review and outcome-blind
characterization.

## 9. Proposed research roadmap

### Stage 0 — Complete the fundamental comparator map

Characterize direct per-square miner-count ordering against raw deployment and
Deployment per Miner. Miner count is fundamental rather than derived, so this
is not a new derived-measurement experiment. It establishes the missing
reference ordering required to interpret every deployment–miner relationship.

### Stage 1 — Mathematical reviews

For each high-priority candidate, prove before implementation:

- exact formula and canonical arithmetic;
- non-equivalence to `D_s`, `M_s`, and `D_s / M_s` orderings;
- zero and tie semantics;
- measurement-level meaning without classification or prediction; and
- revision and protocol dependencies.

Any candidate proved order-equivalent should become a theoretical result and
should not proceed to empirical characterization.

### Stage 2 — Participant-relationship characterizations

Perform future outcome-blind characterizations in this order:

1. signed deployment–miner share imbalance;
2. joint deployment–miner intensity;
3. deployment–miner rank consensus;
4. signed deployment–miner rank gap;
5. per-square discordance burden; and
6. absolute deployment–miner share imbalance.

Each characterization should report exact rank-vector equivalence,
strict/tie-only changes, pairwise divergence, displacement, Top-k membership
changes, and any algebraic overlap with earlier candidates. No outcome source,
baseline, MRR, or prediction belongs in this stage.

### Stage 3 — Protocol-state semantic review

Before characterizing a production-cost-adjusted margin, determine whether the
Board EMA's unit and semantics support the proposed candidate-level
relationship with deployed lamports and miner counts. Failure to prove that
meaning ends the candidate without implementation.

### Stage 4 — Context-only characterization

Characterize participation multiplicity and selected protocol-state scales
only as round-global distributions. Do not present them as candidate rankings.
Advance one toward a future Feature Set only after a separate scientific design
defines a non-arbitrary candidate-varying interaction.

### Stage 5 — Predictive-evaluation candidacy

After each valid outcome-blind characterization, conduct a governance review
to determine whether the signal is sufficiently distinct to merit a future
predictive protocol. This roadmap supplies no authorization and no threshold.
Candidates that fail ordering novelty stop as valid characterization findings.

## 10. Recommendation

The next signal-discovery work should remain in the participant-state domain,
where approved atomic inputs can generate scientifically interpretable and
materially different orderings without unresolved history or cross-revision
semantics.

Begin with direct miner-count comparator characterization, then evaluate
signed deployment–miner share imbalance as the first new derived-measurement
candidate. Follow with joint intensity and rank consensus before considering
more complex discrepancy measures or protocol-state interactions.

Round-global protocol and Treasury relationships should remain low-priority
context research because they cannot rank candidates independently. No item in
this roadmap is approved for implementation, predictive evaluation, Strategy,
or economic use.
