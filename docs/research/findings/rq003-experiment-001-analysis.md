# Finding 001 — RQ-003 Experiment 1 Direct Deployment Ordering

## Status

- Experiment: RQ-003 Experiment 1 — Direct Deployment Ordering
- Governing protocol: revision 3
- Governing source commit:
  `7453cb64013c2a65f8ed99e4b76154bb6a95411f`
- Execution validity: **Valid**
- Scientific interpretation: **Negative evidence**

This finding analyzes only the valid artifacts produced by Official Execution
Attempt #2 under the governing
[Experiment 1 protocol](../experiments/rq003-experiment-001-direct-deployment-ordering.md)
and [RQ-003](../questions/RQ-003-winning-square-predictability.md). It does not
reinterpret the earlier invalid execution.

## 1. Experiment validity

The execution is scientifically valid because every protocol validity gate
completed successfully before the runner returned a result:

- the source commit, execution-specification revision, and Experiment 1
  protocol revision were immutably bound;
- the replay dataset SHA-256 and Replay identity reconstructed;
- the outcome-blind provenance block fixed the replay population, decision
  selection, component identities, and artifact declarations;
- ranking records were frozen before the outcome source was opened;
- the ranking artifact contained no outcome field;
- all ranking procedures used the same decision population and all evaluation
  procedures used the same labeled population;
- external replay bytes and canonical logical content were validated under
  the external-source contract;
- all generated artifacts passed strict canonical encoding, identity,
  dependency, count, hash, and reconstruction validation; and
- the sealed audit manifest records `execution_conformance_result` as
  `passed`.

The audit manifest identity is
`4812859cf03eb14829124fadb639ce4e6c6a36c8054c8915fe2c57643dcee31c`.
The Replay identity is
`e2de7374318bff7d2644b9394106f2ddbf938e9cf8bf4133b3bb5bfe304fe31b`.

## 2. Population

| Population disposition | Rounds | Explanation |
| --- | ---: | --- |
| Replay-bound rounds | 18,653 | Complete immutable Replay population |
| Ranked decisions | 18,651 | A predeclared decision observation existed |
| Pre-ranking exclusions | 2 | No observation existed at or before `end_slot - 5` |
| Finalized outcomes available | 3,507 | Valid labels available after ranking freeze |
| Missing outcomes | 15,146 | No label fabricated or counted as a miss |
| Primary evaluations | 3,198 | Complete lifecycle and valid finalized label |
| Lifecycle-sensitivity evaluations | 309 | Incomplete lifecycle and valid finalized label |

The two pre-ranking exclusions were rounds `342117` and `352002`, both with
reason `no_predeclared_decision_observation`. Both also lacked finalized
outcomes. Consequently, the 15,146 missing outcomes comprise those two
pre-ranking exclusions plus 15,144 ranked decisions excluded at the outcome
join.

Lifecycle coverage across Replay was:

- complete: 17,912;
- partial start: 732;
- partial end: 7; and
- partial both: 2.

Of the available labels, 3,198 complete-lifecycle rounds entered the primary
population. The remaining 309 labeled rounds—308 partial-start and one
partial-end round—were kept outside the primary population and reported only
as the predeclared lifecycle sensitivity. No incomplete lifecycle entered the
primary endpoint.

Outcome availability was 18.801% of Replay; 81.199% remained missing. The
primary population represented 17.145% of Replay. Missingness does not
invalidate the experiment because it was preserved explicitly, no outcome was
imputed, and every chronological fold retained adequate labeled support under
the protocol's threshold.

## 3. Primary endpoint

The identical 3,198-round primary population produced:

| Procedure | MRR |
| --- | ---: |
| Descending deployed lamports | 0.1519459804 |
| Deterministic baseline | 0.1555316799 |
| Seeded-random baseline | 0.1574969091 |

Paired MRR differences were:

- primary minus deterministic baseline: `-0.0035856995`;
- primary minus seeded-random baseline: `-0.0055509287`.

The primary ordering was therefore lower than both required uninformed
baselines on the primary endpoint. Its mean winner rank was `13.1807`, its
median winner rank was `13`, and its Top-1, Top-3, and Top-5 hit rates were
`0.04128`, `0.11757`, and `0.19356`, respectively.

## 4. Bootstrap analysis

The protocol's deterministic circular moving-block bootstrap used 10,000
replicates, block length 15, and adjusted 97.5% percentile intervals:

| Paired comparison | Observed difference | 97.5% interval |
| --- | ---: | ---: |
| Primary − deterministic | -0.0035856995 | [-0.0149039566, 0.0077232220] |
| Primary − seeded random | -0.0055509287 | [-0.0175139334, 0.0058649037] |

Both intervals include zero and have negative lower bounds. The protocol's
statistical-superiority requirement therefore fails for both comparisons.
The intervals permit modest positive or negative differences, so they do not
establish a precisely sized disadvantage; they do establish that the required
positive superiority was not demonstrated.

## 5. Chronological stability

All five consecutive folds exceeded the 100-round adequate-support threshold.

| Fold | Round range | N | Primary MRR | Deterministic MRR | Random MRR | Primary − deterministic | Primary − random |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 342071–352508 | 640 | 0.138123 | 0.140331 | 0.160571 | -0.002208 | -0.022449 |
| 2 | 352522–360802 | 640 | 0.157757 | 0.162933 | 0.157512 | -0.005175 | 0.000245 |
| 3 | 360804–361535 | 640 | 0.153398 | 0.167376 | 0.156597 | -0.013978 | -0.003199 |
| 4 | 361536–362231 | 639 | 0.159496 | 0.160990 | 0.162673 | -0.001493 | -0.003177 |
| 5 | 362232–362955 | 639 | 0.150966 | 0.146022 | 0.150127 | 0.004943 | 0.000839 |

The primary difference was not directionally stable:

- it was below the deterministic baseline in folds 1–4;
- it was below the seeded-random baseline in folds 1, 3, and 4;
- fold 2 exceeded only the seeded-random baseline; and
- fold 5 exceeded both baselines.

Only one of five adequate-support folds had the positive direction against
both baselines. This fails the predeclared fold-consistency requirement.

## 6. Control verification

### Chronology

Replay and evaluation preserved ascending immutable round chronology. All 25
candidates remained grouped within their round. The five folds were
consecutive, contained 639 or 640 rounds, and no random row-level split was
used.

### Protocol revision

The evaluated population was bound to the single supported protocol source
revision `3112ab78a64f92892a70d5d4cbd17e1d14b1c2fe`. Revision identity was
recorded as provenance and validation metadata, not exposed as a ranking
input.

### Decision-distance cadence

Outcome-blind and primary labeled counts were:

| Decision distance | Outcome-blind decisions | Primary evaluations | Adequate labeled support | Primary − deterministic | Primary − random |
| --- | ---: | ---: | --- | ---: | ---: |
| 0 slots | 7,741 | 1,323 | Yes | -0.003060 | -0.010067 |
| 1 slot | 7,650 | 1,290 | Yes | 0.007034 | -0.005521 |
| 2 slots | 3,199 | 571 | Yes | -0.027943 | 0.005958 |
| 3+ slots | 61 | 14 | No | -0.038291 | -0.050879 |

No adequate-support decision-distance stratum exceeded both baselines. The
`3+` group was descriptive only because it had 14 labeled rounds.

### Lifecycle

Only complete lifecycles entered the primary result. The 309 labeled
incomplete lifecycles remained in the separately identified sensitivity
population. Its results did not substitute for the primary endpoint.

### Outcome provenance

Every evaluated outcome was locally observed; there were no enriched or
legacy-unspecified labels. Within the primary population:

| Capture mode | N | Primary MRR | Deterministic MRR | Random MRR |
| --- | ---: | ---: | ---: | ---: |
| Current round | 1,261 | 0.141545 | 0.152983 | 0.157279 |
| Post-transition predecessor | 1,937 | 0.158717 | 0.157191 | 0.157639 |

Capture mode remained outcome provenance only and never entered the ranking.
The two adequately supported capture modes had different observed directions,
so the result was not uniformly favorable across provenance strata.

## 7. Scientific interpretation

**Experiment 1 provides Negative evidence.**

Under the protocol, a valid result that fails any required statistical
superiority condition is negative evidence for the predeclared alternative.
Here:

1. descending deployed-lamport MRR was lower than both baselines;
2. both adjusted bootstrap intervals included zero;
3. the paired difference was not positive in every adequate chronological
   fold; and
4. no adequate decision-distance stratum exceeded both baselines.

The null hypothesis is therefore not rejected. This conclusion is bounded to
the declared measurement, direct descending ordering, `end_slot - 5` decision
boundary, replay population, and protocol revision. It does not establish
that no other eligible decision-time procedure can contain winning-square
information.

## 8. Unexpected observations

- The primary ordering's point estimate was below both uninformed baselines,
  rather than merely indistinguishable from them.
- Fold 5 was the only adequate chronological fold in which the primary
  ordering exceeded both baselines; the preceding four folds did not preserve
  that joint positive direction.
- Current-round outcomes had negative paired differences against both
  baselines, while post-transition-predecessor outcomes had small positive
  paired differences against both. This is a descriptive provenance contrast,
  not a replacement primary result.
- Cadence strata changed direction by baseline: the one-slot group exceeded
  only the deterministic baseline, while the two-slot group exceeded only the
  seeded-random baseline.
- The predeclared ascending sensitivity had MRR `0.1568445`, higher than the
  descending primary MRR but lower than the seeded-random MRR. The protocol
  prohibits using this sensitivity to rescue the primary result.
- Deployment ties were almost absent: one of 18,651 ranked decisions contained
  any tie, and no primary winner belonged to a tie group.

These observations generate bounded questions about temporal and provenance
heterogeneity, but the present artifacts do not establish that cadence or
capture mode causes the differences. Any direct test would require a separate
predeclared protocol.

## 9. Recommendation

**A. Proceed to Experiment 2.**

Experiment 1 was valid, its controls passed, and its predeclared direct
descending ordering failed the required superiority criteria. There is no
experimental defect requiring repetition, and the existing artifacts answer
the Experiment 1 question. Experiment 2 should therefore address a distinct,
prospectively governed research question rather than repeat or post hoc tune
this ordering.
