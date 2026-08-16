# Finding 006 — RQ-003 Experiment 4 Deployment-per-Miner Predictive Evaluation

## Status and scope

- Experiment: RQ-003 Experiment 4 — Deployment-per-Miner Predictive Evaluation
- Governing protocol: revision 1
- Governing source commit:
  `c42e2ef2727bcf86c1cad87d42b065b44c0e5ffd`
- Execution profile: `outcome_aware_v1`
- Execution validity: **Valid**
- Scientific interpretation: **Negative evidence**

This finding reports only the frozen
[Experiment 4 protocol](../experiments/rq003-experiment-004-deployment-per-miner-predictive-evaluation.md),
[RQ-003 Research Execution Specification v2](../specifications/rq003-research-execution-specification-v2.md),
and sealed
[first official Experiment 4 artifacts](../../../data/research/analyses/rq003/experiment-004-deployment-per-miner-predictive-evaluation/first-official-c42e2ef/).
It does not rerun the experiment, alter its methods, perform additional
outcome analysis, select a favorable subgroup, or promote a secondary result
to a new procedure.

## 1. What Experiment 4 tested

Experiment 4 asked whether direct descending ordering by exact frozen
Deployment per Miner contained decision-time information about the eventual
winning square beyond both required uninformed baselines.

For each candidate square `s`, the governed measurement was the canonical
exact rational `deployed_lamports[s] / miner_count[s]` from one frozen
decision observation. The primary procedure ranked all 25 squares directly
by descending Deployment per Miner with exact average-rank tie handling. It
used one predeclared decision point at or before `end_slot - 5` and compared
the identical labeled population with:

- the deterministic ascending-square baseline; and
- the permanently seeded-random baseline.

The predeclared ascending ordering was sensitivity evidence only. It could
not satisfy or rescue the descending primary procedure's success criteria.

## 2. Execution validity

The first official execution is valid under the frozen protocol because:

- source commit `c42e2ef2727bcf86c1cad87d42b065b44c0e5ffd`, protocol
  revision 1, Research Execution Specification v2, and execution profile
  `outcome_aware_v1` were immutably bound;
- the protocol, source, replay dataset, protocol revision, experiment
  configuration, and Replay identities reconstructed;
- the outcome-blind provenance block fixed the Replay population, decision
  selection, measurement and Feature Set identities, procedures, population
  dispositions, and artifact declarations before outcome access;
- the ranking artifact was frozen and validated before the outcome join was
  authorized;
- the primary procedure and both baselines used the identical ranked and
  labeled populations;
- all 12 declared artifacts passed canonical encoding, dependency, digest,
  byte-count, record-count, population-accounting, and reconstruction checks;
- canonical reconstruction and deterministic regeneration were recorded as
  `validated`; and
- the conformance artifact and sealed audit manifest both record `passed`.

No Strategy behavior, deployment action, or RFC-011 economic calculation
entered the experiment.

## 3. Population

| Population disposition | Rounds | Explanation |
| --- | ---: | --- |
| Replay-bound rounds | 18,653 | Complete immutable Replay population |
| Ranked decisions | 18,651 | A valid observation existed at the predeclared decision boundary |
| Pre-ranking exclusions | 2 | No observation existed at or before `end_slot - 5` |
| Finalized outcomes available | 3,507 | Labels joined only after ranking freeze |
| Missing outcomes | 15,146 | No outcome was imputed or counted as a miss |
| Primary evaluations | 3,198 | Complete lifecycle with a valid finalized label |
| Lifecycle-sensitivity evaluations | 309 | Incomplete lifecycle with a valid finalized label |

Population accounting reconciles exactly:

- `18,651 + 2 = 18,653` Replay rounds;
- `3,507 + 15,146 = 18,653` outcome dispositions; and
- `3,198 + 309 = 3,507` available labels.

The two pre-ranking exclusions had disposition
`no_predeclared_decision_observation`. Of the ranked decisions, 15,144 were
excluded from evaluation because outcomes were missing. The remaining two
missing outcomes belonged to the two rounds excluded before ranking.

Lifecycle coverage was 17,912 complete, 732 partial-start, 7 partial-end, and
2 partial-both rounds. Only labeled complete lifecycles entered the primary
endpoint. The 309 labeled incomplete lifecycles remained in the separately
identified sensitivity population.

No decision was excluded for an undefined Deployment-per-Miner measurement.

## 4. Primary endpoint

The identical 3,198-round primary population produced:

| Procedure | MRR | Mean winner rank | Top-1 | Top-3 | Top-5 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Descending Deployment per Miner | 0.1510540210 | 13.1313 | 0.041588 | 0.113821 | 0.189181 |
| Deterministic baseline | 0.1555316799 | 12.9862 | 0.043152 | 0.119450 | 0.211069 |
| Seeded-random baseline | 0.1458166061 | 13.1954 | 0.034396 | 0.113821 | 0.193246 |

Paired MRR differences were:

- primary minus deterministic baseline: `-0.0044776589`; and
- primary minus seeded-random baseline: `0.0052374149`.

The primary point estimate exceeded the seeded-random baseline but was below
the deterministic baseline. The first positive-evidence requirement—higher
MRR than both baselines on the same primary population—was therefore not
satisfied.

## 5. Predeclared statistical decision

The deterministic circular moving-block bootstrap used 10,000 replicates,
block length 15, familywise error rate 0.05, and adjusted 97.5% percentile
intervals:

| Paired comparison | Observed difference | Adjusted 97.5% interval |
| --- | ---: | ---: |
| Primary − deterministic | -0.0044776589 | [-0.0171688541, 0.0090016989] |
| Primary − seeded random | 0.0052374149 | [-0.0058939494, 0.0167755500] |

Both intervals include zero, and neither lower bound is greater than zero.
The predeclared statistical-superiority requirement therefore failed for both
comparisons. The intervals remain compatible with effects in either
direction; they do not establish a precisely sized advantage or disadvantage.

## 6. Secondary and sensitivity evidence

### 6.1 Ascending sensitivity

The predeclared ascending Deployment-per-Miner sensitivity produced:

- MRR: `0.1569013401`;
- mean winner rank: `12.8687`;
- Top-1 hit rate: `0.043152`;
- Top-3 hit rate: `0.128831`; and
- Top-5 hit rate: `0.206066`.

This secondary direction was not the primary procedure and cannot rescue the
failed descending result or be promoted from this finding into a Strategy.

### 6.2 Lifecycle sensitivity

The 309 labeled incomplete-lifecycle evaluations produced:

| Procedure | MRR |
| --- | ---: |
| Descending Deployment per Miner | 0.1524657276 |
| Deterministic baseline | 0.1885437267 |
| Seeded-random baseline | 0.1547581147 |
| Ascending sensitivity | 0.1795440080 |

The lifecycle primary difference was `-0.0360779991` against the
deterministic baseline and `-0.0022923871` against the seeded-random baseline.
This separately governed sensitivity did not replace the complete-lifecycle
primary population.

### 6.3 Chronological stability

All five consecutive folds had adequate labeled support, but paired
differences were directionally inconsistent:

| Fold | Round range | N | Primary − deterministic | Primary − random |
| ---: | --- | ---: | ---: | ---: |
| 1 | 342071–352508 | 640 | 0.0066384871 | -0.0046848624 |
| 2 | 352522–360802 | 640 | -0.0087833550 | 0.0098356996 |
| 3 | 360804–361535 | 640 | -0.0366442213 | -0.0131765526 |
| 4 | 361536–362231 | 639 | 0.0011508590 | 0.0233863774 |
| 5 | 362232–362955 | 639 | 0.0152896168 | 0.0108635611 |

Only folds 4 and 5 were positive against both baselines. Fold 3 was negative
against both, while folds 1 and 2 changed direction by comparator. The
required positive direction against both baselines was not preserved across
all adequately supported folds.

### 6.4 Decision-distance cadence

| Decision distance | Ranked decisions | Primary N | Adequate support | Primary − deterministic | Primary − random |
| --- | ---: | ---: | --- | ---: | ---: |
| 0 slots | 7,741 | 1,323 | Yes | -0.0000489831 | 0.0045663228 |
| 1 slot | 7,650 | 1,290 | Yes | 0.0028796366 | 0.0065628639 |
| 2 slots | 3,199 | 571 | Yes | -0.0303095645 | 0.0061720427 |
| 3+ slots | 61 | 14 | No | -0.0473370219 | -0.0915944968 |

Only the one-slot stratum was positive against both baselines. The `3+`
stratum had 14 labeled evaluations and lacked the required support, so it is
descriptive only.

### 6.5 Outcome provenance

All primary labels were locally observed. No enriched or
legacy-unspecified outcome entered the evaluation.

| Outcome provenance | N | Primary MRR | Deterministic MRR | Random MRR | Primary − deterministic | Primary − random |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `current_round` | 1,261 | 0.141734 | 0.152983 | 0.153248 | -0.011249 | -0.011513 |
| `post_transition_predecessor` | 1,937 | 0.157121 | 0.157191 | 0.140979 | -0.000070 | 0.016142 |

The two adequately supported provenance groups showed different comparator
patterns. This is a predeclared stratification result. Outcome provenance was
evaluation metadata only, never a ranking input, and this contrast does not
authorize a subgroup-specific procedure or post-hoc Strategy adjustment.

## 7. Ties, exclusions, and observed limitations

- One of 18,651 ranked decisions contained one two-candidate tie; all other
  candidate groups were singletons.
- No evaluated winning candidate was tied.
- No undefined Deployment-per-Miner value occurred.
- Two Replay rounds lacked the predeclared decision observation and were not
  repaired or replaced.
- Outcomes were missing for 15,146 Replay rounds, including 15,144 ranked
  decisions. No missing label was imputed.
- The primary result is based on 3,198 complete-lifecycle labeled rounds from
  the bound Replay population and protocol revision.
- The `3+` decision-distance stratum lacked adequate labeled support.
- Chronological, cadence, lifecycle, and provenance evidence did not preserve
  one uniformly favorable direction against both baselines.

These limitations are part of the frozen result. They do not invalidate the
execution because every exclusion and disposition was predeclared, preserved,
and reconciled.

## 8. Scientific interpretation

**Experiment 4 provides Negative evidence.**

At the predeclared decision point, descending Deployment-per-Miner ranking did
not satisfy the predeclared positive-evidence criteria for predicting the
eventual winning square:

1. its primary MRR was below the deterministic baseline;
2. both adjusted paired bootstrap intervals included zero;
3. paired differences were not positive against both baselines in every
   adequately supported chronological fold;
4. the direction was not stable across adequately supported
   decision-distance strata; and
5. the two adequately supported outcome-provenance groups did not both show
   superiority to both baselines.

The null hypothesis is not rejected under the protocol. Deployment per Miner,
as defined and evaluated in Experiment 4, is not supported as a predictive
ranking signal for winner selection at the tested decision point.

This bounded conclusion does **not** establish that:

- deployment information can never contain useful decision-time signal;
- every relationship or prospectively governed combination of participant
  measurements must fail;
- ascending Deployment per Miner is a validated alternative procedure;
- the result has any profitability implication; or
- live deployment is justified.

## 9. Provenance and reproducibility

| Binding | Identity |
| --- | --- |
| Governing source commit | `c42e2ef2727bcf86c1cad87d42b065b44c0e5ffd` |
| Protocol SHA-256 | `356f7b2c2d9e24520983e9f692675f6f6c432b7741ce1066a29b6f11b9d407b5` |
| Dataset SHA-256 | `7680856bc6a01f9b69be0921d6e66b3f43d5241a38e63b37871b6925c1d59ba7` |
| Replay identity | `885f4b8c5c064692d86ea7d5dbd2d5ca93ea238b504c80bed3e7945e2676e1fb` |
| Source provenance identity | `ac9cca2f188e63e9d87bd03786345b949630f698aad36549facf1d329318a732` |
| Execution specification identity | `ae246a7a93e60316e375c6efe2cddb1a7e8e19ac82e5272420e43903b4bf79ca` |
| Execution profile identity | `c0f8008f659865f2c0e45daf3d858ce5db61d08c4e6f385b0431f9f542b73851` |
| Audit manifest identity | `04f64bace113ebc3301b6e6db26a6fa90342636e74a72614c37659129bdc2cd9` |

The sealed audit manifest SHA-256 is
`5bbe927dbec234f90f43c403750e0a6e9cd6db963b8c7dfe788212a2d4b2ecaa`.
The authoritative execution artifacts remain under the linked first-official
artifact root.

## 10. Research-program implication

Experiment 4 completes the bounded predictive question for direct descending
Deployment-per-Miner ordering at the tested decision point. Its structural
novelty relative to raw Deployment, established by Finding 002, did not
translate into the positive predictive evidence required by the Experiment 4
protocol.

The research program must retain this as a valid negative result. It provides
no basis for live deployment, profitability claims, post-hoc promotion of the
ascending sensitivity, or modification of Experiment 4. Any future research
question remains separately governed and is not authorized by this finding.
