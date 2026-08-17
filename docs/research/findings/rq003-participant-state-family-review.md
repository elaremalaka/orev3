# RQ-003 Participant-State Family Review

## Status and scope

- Type: Research review
- Implementation authorized: No
- Predictive evaluation authorized by this document: No
- Decision-engine design authorized by this document: No

This review uses only:

- [Finding 001](rq003-experiment-001-analysis.md);
- [Finding 002](rq003-experiment-002-analysis.md);
- [Finding 003](rq003-experiment-002c-analysis.md);
- the sealed [Experiment 2D execution artifacts](../../../data/research/analyses/rq003/experiment-002d-share-imbalance-characterization/first-official-b09400d/); and
- the [RQ-003 Signal Discovery Roadmap](../investigations/rq003-signal-discovery-roadmap.md).

For this review, **Finding 004** means the scientific result reconstructed
directly from the valid Experiment 2D execution artifacts. This usage does not
assume or create a separate Finding 004 document.

The review evaluates scientific maturity and next-phase direction. It does
not introduce a measurement, define an experiment, select a Feature Set,
propose implementation, or authorize Strategy or production use.

## 1. Findings 001–004

### 1.1 Finding 001 — Direct Deployment ordering

**Scientific question:** Does direct descending ordering by frozen
protocol-published deployed lamports contain decision-time information about
the eventual winning square beyond the required uninformed baselines?

**Result:** Negative evidence under the governed Experiment 1 protocol. On
3,198 complete-lifecycle evaluated rounds, direct Deployment MRR was
`0.1519459804`, compared with deterministic-baseline MRR `0.1555316799` and
seeded-random-baseline MRR `0.1574969091`. Both adjusted bootstrap intervals
for the paired differences included zero, and the required chronological and
decision-distance consistency conditions were not satisfied.

**Remaining uncertainty:** The result is bounded to direct descending
Deployment, the governed decision boundary, population, revision, and
evaluation procedure. It does not determine whether Miner Count, Deployment
per Miner, Signed Share Imbalance, or a separately governed multi-signal
procedure contains predictive information.

### 1.2 Finding 002 — Deployment-per-Miner ordering

**Scientific question:** Does exact Deployment-per-Miner ordering materially
change candidate ordering relative to raw Deployment?

**Result:** Yes, at the ordering-characterization boundary. All 17,912
eligible decisions contained strict ordering changes. Mean pairwise
disagreement was approximately `92.7432` of 300 candidate pairs, mean total
rank displacement was approximately `134.3138`, and Top-1 membership changed
in `65.0234%` of decisions. No outcome was accessed.

**Remaining uncertainty:** Finding 002 establishes ordering novelty, not
winning-square information. It does not show that Deployment per Miner is
superior to Deployment, a baseline, or any other ordering.

### 1.3 Finding 003 — Miner Count ordering

**Scientific question:** Does direct Miner Count ordering materially differ
from raw Deployment and Deployment-per-Miner ordering?

**Result:** Yes, for both comparisons. All 17,912 eligible decisions contained
strict changes against each reference. Miner Count disagreed with Deployment
on a mean of approximately `163.1639` candidate pairs and with Deployment per
Miner on approximately `255.9071` pairs. Miner Count also preserved a distinct
tie structure: every eligible decision contained Miner Count ties, while the
two references were almost entirely tie-free.

**Remaining uncertainty:** No outcome was accessed. The result does not
establish whether Miner Count's distinct ordering or tie structure contains
predictive information.

### 1.4 Finding 004 — Signed Deployment–Miner Share Imbalance ordering

**Scientific question:** Does descending exact Signed Deployment–Miner Share
Imbalance materially differ from raw Deployment, Miner Count, and Deployment
per Miner?

**Result:** The valid Experiment 2D artifacts establish three bounded results
over 17,912 eligible decisions:

| Comparison | Identical rank vectors | Tie-only changes | Strict changes | Mean pairwise disagreements | Mean total rank displacement |
| --- | ---: | ---: | ---: | ---: | ---: |
| Share Imbalance vs Deployment | 0 | 0 | 17,912 | 92.7726 | 134.3306 |
| Share Imbalance vs Miner Count | 0 | 0 | 17,912 | 255.9365 | 289.2788 |
| Share Imbalance vs Deployment per Miner | 8,980 | 0 | 8,932 | 0.7635 | 1.5073 |

Share Imbalance therefore strictly differs from Deployment and Miner Count in
every eligible decision. Its relationship with Deployment per Miner is much
closer: the average-rank vectors are identical in 8,980 decisions
(`50.1340%`) and strictly different in 8,932 (`49.8660%`). Where differences
occur, they are strict rather than tie-only, but their population-average
magnitude is small compared with the other two comparisons.

Top-k membership changes reinforce that distinction:

| Comparison | Top-1 changed | Top-3 changed | Top-5 changed |
| --- | ---: | ---: | ---: |
| Share Imbalance vs Deployment | 63.2537% | 89.9453% | 91.9998% |
| Share Imbalance vs Miner Count | 99.7823% | 100% | 100% |
| Share Imbalance vs Deployment per Miner | 3.0147% | 4.6449% | 4.5109% |

Every decision passed the exact zero-sum invariant. The population contained
no zero-valued Share Imbalance candidate: each decision had both positive and
negative values, as required by its exact signed distribution.

Execution was valid under `outcome_blind_characterization_v1`; all artifacts
reconstructed, deterministic regeneration was byte-identical, and outcome
access was `prohibited_and_not_performed`.

**Remaining uncertainty:** Finding 004 establishes ordering structure only.
It does not determine whether Share Imbalance predicts winners, whether its
small differences from Deployment per Miner matter for predictive evaluation,
or whether either ordering is scientifically preferable.

## 2. Participant-state signal map

The four core signals represent different views of one frozen participant
state.

| Signal | Observable represented | Distinct contribution | Principal overlap |
| --- | --- | --- | --- |
| Deployment | Per-square protocol-published deployed-lamport magnitude | Direct capital-distribution ordering; nearly tie-free | Fundamental input to Deployment per Miner and Share Imbalance |
| Miner Count | Per-square protocol-published Miner membership magnitude | Participation-distribution ordering and substantial tie structure | Fundamental input to Deployment per Miner and Share Imbalance |
| Deployment per Miner | Exact local relationship `D_s / M_s` | Candidate-local deployment relative to membership; resolves most Miner Count ties | Shares both atomic inputs with the other participant relationships |
| Signed Deployment–Miner Share Imbalance | Exact difference between a square's Deployment share and Miner share | Directional disagreement between the complete board distributions | Empirically close to Deployment per Miner, but not order-equivalent |

### 2.1 Deployment

Deployment retains direct magnitude and is the only core signal with a
completed predictive evaluation. That evaluation produced negative evidence
for its direct descending use. Deployment remains necessary as a fundamental
measurement and reference ordering, but it is not a validated decision rule.

### 2.2 Miner Count

Miner Count supplies the most structurally different direct ordering in the
core map. It differs extensively from Deployment, Deployment per Miner, and
Share Imbalance, and its tie structure is not reproduced by the other
orderings. This is independent observable ordering structure, not demonstrated
predictive information.

### 2.3 Deployment per Miner

Deployment per Miner relates the two atomic participant measurements locally.
It differs materially from Deployment and Miner Count but overlaps strongly
with Share Imbalance. The overlap is empirical rather than algebraic identity:
nearly half of eligible decisions still contain a strict difference between
the two relationship orderings.

### 2.4 Signed Deployment–Miner Share Imbalance

Share Imbalance relates each candidate to both complete board distributions.
It preserves the direction of distributional disagreement and sums exactly to
zero. Its ordering is distinct from both direct measurements, while its close
relationship with Deployment per Miner identifies an important redundancy
boundary within the family.

## 3. Characterization coverage

Among the four core orderings, no pairwise ordering relationship remains
scientifically uncharacterized.

There are six unordered pairs, and the accepted evidence covers all six:

| Pair | Evidence |
| --- | --- |
| Deployment vs Deployment per Miner | Finding 002 |
| Deployment vs Miner Count | Finding 003 |
| Miner Count vs Deployment per Miner | Finding 003 |
| Share Imbalance vs Deployment | Finding 004 |
| Share Imbalance vs Miner Count | Finding 004 |
| Share Imbalance vs Deployment per Miner | Finding 004 |

The broader participant-state roadmap is not exhausted. It already identifies
additional, uncharacterized participant relationships, including Joint
Deployment–Miner Intensity, Deployment–Miner Rank Consensus, Signed
Deployment–Miner Rank Gap, per-square Discordance Burden, and Absolute Share
Imbalance. Those are existing roadmap candidates, not findings and not
approved decision signals.

The relevant maturity distinction is therefore:

- the **core participant-state comparator map is complete**; and
- the **space of possible derived participant-state measurements remains
  open**.

## 4. Strongest remaining unknowns

The largest remaining uncertainties are no longer about whether the four core
orderings differ. They are:

1. **Predictive information:** Miner Count, Deployment per Miner, and Share
   Imbalance have not been evaluated against outcomes or uninformed baselines.
2. **Relative predictive contribution:** The evidence cannot determine
   whether their ordering differences correspond to useful information or
   noise.
3. **Incremental value:** The close Share-Imbalance/Deployment-per-Miner
   relationship raises an unresolved question about whether the 8,932 strict
   differences contribute anything beyond their shared ordering.
4. **Tie treatment:** Miner Count's extensive ties are characterized but have
   not been evaluated under a predictive protocol.
5. **Temporal and provenance stability:** No predictive result exists for the
   three unevaluated signals, so chronological, decision-distance, lifecycle,
   and outcome-provenance stability remain unknown.
6. **Generalization:** All accepted results remain bound to the governed Replay
   population, decision boundary, and protocol revision.
7. **Combination value:** No accepted evidence shows that combining core
   signals improves a decision. A decision engine cannot infer this from
   ordering novelty alone.

## 5. Diminishing returns from further characterization

Further characterization is likely to produce diminishing scientific returns
if it continues before any predictive evaluation of the core signals.

The reason is not that participant-state characterization is complete in the
absolute sense. The roadmap contains mathematically distinct candidates that
could produce new orderings. Rather, the most important structural questions
for the four core signals have already been answered:

- all six pairwise relationships are known;
- direct versus relationship orderings are empirically distinct;
- tie-only and strict differences are separated;
- divergence, displacement, Top-k membership, and tie distributions are
  quantified; and
- Share Imbalance's major overlap with Deployment per Miner is now visible.

Another outcome-blind ordering can add structural variety, but it cannot
answer the dominant remaining question: whether any unevaluated core signal
contains winning-square information. Continuing to generate distinct
orderings without testing that question risks accumulating mathematically
novel but scientifically unprioritized transformations.

Characterization remains appropriate when a new roadmap candidate requires
it, but it is no longer the highest-value next phase for the family as a whole.

## 6. Direction assessment

### 6.1 A — Continue participant-state characterization

**Expected scientific value:** Moderate. Existing roadmap candidates could
clarify joint magnitude, rank agreement, directional rank gaps, or discordance
structure. Each could extend the map beyond the four core signals.

**Expected contribution toward a practical miner:** Indirect. It would
increase the catalog of distinct observables but would not determine whether
any helps choose a square.

**Remaining uncertainty:** Predictive value would remain entirely unresolved
for every newly characterized signal. The family would gain breadth without
closing its most important evidence gap.

### 6.2 B — Begin predictive evaluation of participant-state signals

**Expected scientific value:** High. This direction directly addresses the
strongest remaining unknown: whether the ordering novelty established for
Miner Count, Deployment per Miner, and Share Imbalance corresponds to
decision-time information beyond uninformed baselines.

**Expected contribution toward a practical miner:** Direct but conditional.
A valid predictive evaluation could identify negative, positive, or
inconclusive evidence for the existing signals. Any of those outcomes would
materially narrow the design space for a future decision engine.

**Remaining uncertainty:** Predictive protocols would still need prospective
controls for chronology, revision, lifecycle, decision distance, outcome
provenance, baselines, uncertainty, and interpretation. Ordering novelty does
not imply that a positive result will occur.

### 6.3 C — Begin experimental decision-engine design

**Expected scientific value:** Low at the current boundary. Engine design
would require choices about signal inclusion, combination, ranking, and
conflict resolution before the predictive contribution of three of the four
core signals is known.

**Expected contribution toward a practical miner:** Premature and uncertain.
Finding 001 supplies negative evidence for direct Deployment, while Findings
002–004 supply no predictive evidence. Architecture built now would encode
untested scientific assumptions.

**Remaining uncertainty:** Nearly every decision-engine choice would be
unsupported: which signals to include, whether Share Imbalance adds value
beyond Deployment per Miner, how to treat Miner Count ties, whether signals
should be combined, and whether any candidate improves on uninformed
baselines.

## 7. Recommendation

**B. Begin predictive evaluation of participant-state signals.**

The participant-state family is scientifically mature enough to leave
characterization as its default next activity. The core four-signal comparator
map is complete, and the largest remaining uncertainty is predictive rather
than structural. Predictive evaluation of the already characterized signals
offers more scientific value than adding another ordering and is a necessary
precondition for evidence-based decision-engine design.

This recommendation identifies the next scientific phase only. It does not
authorize an experiment, select an evaluation order, define a Feature Set,
change governance, or begin decision-engine implementation.
