# Finding 005 — RQ-003 Experiment 3 Miner Count Predictive Evaluation

## Status and scope

- Experiment: RQ-003 Experiment 3 — Miner Count Predictive Evaluation
- Governing protocol: revision 1
- Governing source commit:
  `7f0418fbefa78de883d9e2590f7f6de031989811`
- Execution profile: `outcome_aware_v1`
- Execution validity: **Valid**
- Scientific interpretation: **Negative evidence**

This finding analyzes only the governing
[Experiment 3 protocol](../experiments/rq003-experiment-003-miner-count-predictive-evaluation.md),
[RQ-003 Research Execution Specification v2](../specifications/rq003-research-execution-specification-v2.md),
and the sealed
[first official Experiment 3 artifacts](../../../data/research/analyses/rq003/experiment-003-miner-count-predictive-evaluation/first-official-7f0418f/).
It does not rerun the experiment, alter the protocol, tune a procedure, or
interpret any result outside the protocol's predeclared rules.

## 1. Execution validity

The execution is scientifically valid because every required binding,
boundary, and reconstruction check passed:

- source commit `7f0418fbefa78de883d9e2590f7f6de031989811`, Research
  Execution Specification v2, protocol revision 1, and execution profile
  `outcome_aware_v1` were immutably bound;
- replay dataset SHA-256
  `7680856bc6a01f9b69be0921d6e66b3f43d5241a38e63b37871b6925c1d59ba7`
  and Replay identity
  `1ebe70716be53315299a96c4c1162034dcfb63a5a231e42b1e6d6df115b5ef4f`
  reconstructed successfully;
- the frozen outcome-blind provenance block fixed the Replay population,
  decision selection, one-field Feature Set, procedure identities, population
  dispositions, and artifact declarations before outcome access;
- the ranking artifact was frozen and validated before the outcome join was
  authorized;
- the primary procedure and both baselines used identical ranked and labeled
  populations;
- all 12 required artifacts passed canonical encoding, identity, dependency,
  digest, byte-count, record-count, population-reconciliation, and
  reconstruction validation;
- deterministic regeneration and canonical reconstruction were recorded as
  `validated`; and
- the conformance result and sealed Experiment Audit Manifest both record
  `passed`.

The audit-manifest identity is
`76d61817bb9765ab7071983d1c4e4279487d7add2130880d3c1a4a87a2714208`.
The outcome-blind provenance identity is
`ba0de1a38dcd36fe26ca7fe6c2ccc3566322844b4ae649f0ab18b5d18e1b4b2c`.

## 2. Population

| Population disposition | Rounds | Explanation |
| --- | ---: | --- |
| Replay-bound rounds | 18,653 | Complete immutable Replay population |
| Ranked decisions | 18,651 | A valid observation existed at the predeclared decision boundary |
| Pre-ranking exclusions | 2 | No observation existed at or before `end_slot - 5` |
| Finalized outcomes available | 3,507 | Valid labels joined only after ranking freeze |
| Missing outcomes | 15,146 | No outcome was imputed or counted as a miss |
| Primary evaluations | 3,198 | Complete lifecycle with a valid finalized label |
| Lifecycle-sensitivity evaluations | 309 | Incomplete lifecycle with a valid finalized label |

Population accounting reconciles exactly:

- `18,651 + 2 = 18,653` Replay rounds;
- `3,507 + 15,146 = 18,653` outcome dispositions; and
- `3,198 + 309 = 3,507` available labels.

Lifecycle coverage was 17,912 complete, 732 partial-start, 7 partial-end, and
2 partial-both rounds. Only the 3,198 labeled complete lifecycles entered the
primary endpoint. The 309 labeled incomplete lifecycles remained in the
separately identified sensitivity population. The two pre-ranking exclusions
had disposition `no_predeclared_decision_observation`; no substitute decision
was selected.

Missing outcomes represented 81.1987% of Replay. They remained explicitly
accounted for and did not affect the outcome-blind ranking population.

## 3. Primary endpoint

The identical 3,198-round primary population produced:

| Procedure | MRR |
| --- | ---: |
| Descending Miner Count | 0.1544988411 |
| Deterministic baseline | 0.1555316799 |
| Seeded-random baseline | 0.1506855540 |

Paired MRR differences were:

- Miner Count minus deterministic baseline: `-0.0010328387`;
- Miner Count minus seeded-random baseline: `0.0038132871`.

Descending Miner Count therefore exceeded the seeded-random baseline point
estimate but did not exceed the deterministic baseline. The first success
criterion, which requires higher MRR than both baselines on the identical
primary population, was not satisfied.

## 4. Bootstrap analysis

The predeclared deterministic circular moving-block bootstrap used 10,000
replicates, block length 15, and Bonferroni-adjusted 97.5% percentile
intervals:

| Paired comparison | Observed difference | Adjusted 97.5% interval |
| --- | ---: | ---: |
| Miner Count − deterministic | -0.0010328387 | [-0.0083770015, 0.0063025482] |
| Miner Count − seeded random | 0.0038132871 | [-0.0080638175, 0.0158093505] |

Both intervals include zero, and neither lower bound is greater than zero.
The protocol's statistical-superiority requirement therefore fails for both
comparisons. The intervals remain compatible with small effects in either
direction; they do not establish a precisely sized advantage or disadvantage.

## 5. Chronological stability and predeclared controls

### 5.1 Chronological folds

All five consecutive folds had adequate labeled support.

| Fold | Round range | N | Miner Count MRR | Deterministic MRR | Random MRR | Miner Count − deterministic | Miner Count − random |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 342071–352508 | 640 | 0.148479 | 0.140331 | 0.149461 | 0.008148 | -0.000982 |
| 2 | 352522–360802 | 640 | 0.152732 | 0.162933 | 0.157900 | -0.010201 | -0.005168 |
| 3 | 360804–361535 | 640 | 0.168210 | 0.167376 | 0.149726 | 0.000833 | 0.018484 |
| 4 | 361536–362231 | 639 | 0.157097 | 0.160990 | 0.144156 | -0.003893 | 0.012940 |
| 5 | 362232–362955 | 639 | 0.145968 | 0.146022 | 0.152177 | -0.000055 | -0.006210 |

Only fold 3 preserved a positive direction against both baselines. Fold 2 and
fold 5 were negative against both; fold 1 exceeded only the deterministic
baseline; and fold 4 exceeded only the seeded-random baseline. The required
fold-by-fold positive direction against both baselines was not present.

### 5.2 Decision-distance strata

Decision distance is the predeclared audit variable
`(end_slot - 5) - selected_observation_slot`.

| Distance | Ranked decisions | Primary N | Adequate support | Miner Count − deterministic | Miner Count − random |
| --- | ---: | ---: | --- | ---: | ---: |
| 0 | 7,741 | 1,323 | Yes | -0.002118 | -0.001095 |
| 1 | 7,650 | 1,290 | Yes | 0.007835 | 0.012386 |
| 2 | 3,199 | 571 | Yes | -0.017174 | -0.002354 |
| 3+ | 61 | 14 | No | -0.057303 | -0.070690 |

The one-slot stratum was positive against both baselines, while the other two
adequately supported strata were negative against both. The `3+` stratum was
descriptive only because its 14 labeled rounds were below the support
threshold. The observed direction was therefore not stable across adequately
supported decision-distance strata.

### 5.3 Lifecycle

Only complete lifecycles entered the primary endpoint. The 309 labeled
incomplete lifecycles produced a sensitivity difference of `-0.0163693`
against the deterministic baseline and `0.0308194` against the seeded-random
baseline. This mixed sensitivity did not replace or rescue the primary result.

### 5.4 Outcome provenance

All 3,198 primary labels were locally observed; no enriched or
legacy-unspecified outcome entered the evaluation.

| Outcome provenance | N | Miner Count MRR | Deterministic MRR | Random MRR | Miner Count − deterministic | Miner Count − random |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `current_round` | 1,261 | 0.154383 | 0.152983 | 0.150803 | 0.001400 | 0.003581 |
| `post_transition_predecessor` | 1,937 | 0.154574 | 0.157191 | 0.150609 | -0.002617 | 0.003965 |

Both provenance groups had adequate support. The current-round group was
positive against both baselines, whereas the post-transition-predecessor group
was below the deterministic baseline. Outcome provenance remained evaluation
metadata only and did not enter ranking or pre-outcome eligibility.

## 6. Control verification

| Control | Result | Evidence |
| --- | --- | --- |
| Chronology | Passed | Replay order was `start_slot_then_round_id`; five consecutive folds preserved the round as the independent unit. |
| Outcome isolation | Passed | Ranking and outcome-blind provenance were frozen before authorized outcome access; outcome attachment did not alter ranking identities. |
| Protocol revision | Passed | One supported protocol source revision, `3112ab78a64f92892a70d5d4cbd17e1d14b1c2fe`, was used only as immutable provenance and validation metadata. |
| Deterministic execution | Passed | The conformance artifact records deterministic regeneration as `validated`. |
| Canonical reconstruction | Passed | Replay, measurement, Feature Set, ranking, artifact-contract, provenance, and audit-manifest identities reconstructed. |
| Population parity | Passed | Descending Miner Count and both baselines ranked the same decisions and evaluated the same labeled rounds. |
| Lifecycle and cadence | Passed | Complete lifecycles alone formed the primary population; every observation-count and decision-distance population reconciled. |

No Strategy behavior, deployment action, or RFC-011 economic calculation
entered the experimental path.

## 7. Scientific interpretation

**Experiment 3 provides Negative evidence.**

The execution is valid, but the predeclared alternative is not supported:

1. descending Miner Count MRR was lower than the deterministic baseline;
2. both adjusted paired bootstrap intervals included zero;
3. only one of five adequately supported chronological folds was positive
   against both baselines;
4. only one of three adequately supported decision-distance strata was
   positive against both baselines; and
5. the positive direction was not preserved across both adequately supported
   outcome-provenance groups.

Section 12.2 of the protocol classifies a valid result that fails a required
statistical-superiority condition as negative evidence. Superiority to only
the seeded-random baseline cannot overturn that disposition.

The conclusion is bounded to frozen per-square Miner Count, direct descending
ordering, the `end_slot - 5` decision boundary, this Replay population, and
the supported protocol revision. It does not establish that Miner Count lacks
incremental value in every separately governed relationship or combined
procedure.

## 8. Participant-state roadmap implications

### Deployment

The Experiment 3 protocol records Finding 001's negative result for direct
descending Deployment ordering. Experiment 3 does not alter that finding.
Together, the two valid predictive experiments provide negative evidence for
both direct fundamental participant-state orderings under their governed
decision boundary and uninformed-baseline tests.

### Miner Count

Miner Count was structurally distinct enough to warrant its own predictive
evaluation, but structural distinctness did not translate into the protocol's
required predictive superiority. Direct descending Miner Count ordering is
therefore scientifically answered for this bounded population and should not
be promoted as a standalone ranking signal on the basis of these artifacts.

### Deployment per Miner

Experiment 3 did not evaluate Deployment per Miner. Its predictive question
remains open. The Miner Count result neither supplies positive evidence for
that relationship signal nor eliminates it: Deployment per Miner combines two
fundamental measurements through a separately governed ordering and requires
its own prospective predictive protocol before any conclusion is possible.

### Signed Share Imbalance

Experiment 3 did not evaluate Signed Deployment–Miner Share Imbalance. Its
predictive question also remains open. Because it represents a relationship
between the two participant-state distributions rather than either direct
fundamental ordering alone, the negative direct-ordering results do not decide
its behavior.

The participant-state roadmap should therefore treat direct Deployment and
direct Miner Count as completed negative evaluations while leaving Deployment
per Miner and Share Imbalance as unevaluated predictive questions. Experiment
3 supplies no basis for prioritizing one of those relationship signals over
the other, combining signals, admitting any signal to Strategy, or making a
deployment decision. Each next step remains subject to its own prospective
protocol and authorization.
