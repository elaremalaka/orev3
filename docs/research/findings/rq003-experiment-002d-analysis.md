# Finding 004 — RQ-003 Experiment 2D Signed Deployment–Miner Share Imbalance Characterization

## Retrospective archival status

This is a **retrospective archival reconstruction** of the historical RQ-003
Experiment 2D result. Experiment 2D was executed and sealed before this
standalone Finding 004 document was created.

No contemporaneous standalone Finding 004 document has been found in the
repository history. The label **Finding 004** was first found retrospectively
in the later
[Participant-State Family Review](rq003-participant-state-family-review.md),
which reconstructed the Experiment 2D result directly from its sealed
artifacts. Creating this document does not claim that a standalone Finding
004 existed when Experiment 2D was conducted.

This finding records the already-sealed valid evidence without rerunning the
experiment, regenerating an artifact, calculating a new metric, or performing
new scientific analysis.

## Status and scope

- Experiment: RQ-003 Experiment 2D — Signed Deployment–Miner Share Imbalance
  Characterization
- Governing protocol: revision 1
- Governing source commit:
  `b09400d723d7bb9cd72efcf2b45c986eef000bb8`
- Execution specification: `rq003-research-execution-specification-v2`
- Execution profile: `outcome_blind_characterization_v1`
- Historical execution validity: **Valid**
- Scientific boundary: **Outcome-blind ordering characterization**

This finding reports only the frozen
[Experiment 2D protocol](../experiments/rq003-experiment-002d-share-imbalance-characterization.md),
[RQ-003 Research Execution Specification v2](../specifications/rq003-research-execution-specification-v2.md),
and sealed
[first official Experiment 2D artifacts](../../../data/research/analyses/rq003/experiment-002d-share-imbalance-characterization/first-official-b09400d/).
It does not use a later predictive result to reinterpret Experiment 2D.

## 1. Experiment identity and purpose

Experiment 2D asked whether descending exact Signed Deployment–Miner Share
Imbalance produced a materially different candidate ordering from:

1. descending raw Deployment;
2. descending Miner Count; and
3. descending Deployment per Miner.

The experiment characterized ordering structure only. It did not ask whether
Share Imbalance predicted an eventual winning square or outperformed another
procedure.

## 2. Historical execution-attempt history

### 2.1 Invalid immutable-source preflight attempt

The first requested governing commit was
`3ba070ba3c2173d63df690054c4c91957b640db9`. That commit contained the
Experiment 2D implementation, but it did not contain the Experiment 2D
protocol. Immutable-source preflight therefore failed, and the attempt was
**invalid**.

No authoritative scientific evidence is attributed to that attempt. No
retained Experiment 2D artifact root was established for it.

### 2.2 Authoritative valid execution

The protocol was subsequently frozen at source commit
`b09400d723d7bb9cd72efcf2b45c986eef000bb8`. The execution under that commit
produced the sealed `first-official-b09400d` artifact set. Its conformance
artifact records `passed`, deterministic reconstruction as `validated`, and
outcome access as `prohibited_and_not_performed`.

This second execution is the sole authoritative evidence for this finding.

## 3. Authoritative execution and provenance

| Binding | Authoritative value |
| --- | --- |
| Governing source commit | `b09400d723d7bb9cd72efcf2b45c986eef000bb8` |
| Protocol revision | `1` |
| Protocol SHA-256 | `3fb25bbbcac39d03243418468c37a571fce282f1d4ee6bdacfe010813b29d90a` |
| Protocol source revision | `3112ab78a64f92892a70d5d4cbd17e1d14b1c2fe` |
| Source provenance identity | `f5aa4c78334fb3abbd8ae992aa8d697db3031ff55ac8bd541839c8f7d32babf4` |
| Replay identity | `ae796fdeaecf5f703d4c36049fd69747b71de3ed89f158df344579c8f1859925` |
| Audit-manifest identity | `26ed05c6c8d465cd67be1477a50fa8c28bda64dcc3e6856dca292c013c4cb2c1` |
| Execution-specification identity | `ae246a7a93e60316e375c6efe2cddb1a7e8e19ac82e5272420e43903b4bf79ca` |
| Execution profile | `outcome_blind_characterization_v1` |
| Execution-profile identity | `0ee29e9c2382e2e3ea8e777760a7782f67b123d14402f8cc5be2a25a4d7c41ba` |
| Dataset SHA-256 | `7680856bc6a01f9b69be0921d6e66b3f43d5241a38e63b37871b6925c1d59ba7` |
| Dataset identity | `f833a58a758d74b71afdb3054751c11b115f3175885fb8bf50b59275ef014f93` |
| Outcome access | `prohibited_and_not_performed` |

## 4. Population and exclusions

| Population disposition | Decisions | Explanation |
| --- | ---: | --- |
| Replay rounds | 18,653 | Complete bound Replay population |
| Eligible decisions | 17,912 | Complete lifecycle and all governed measurement and ordering requirements satisfied |
| Excluded decisions | 741 | Deterministic disposition `incomplete_lifecycle` |
| Zero-sum validations passed | 17,912 | Every eligible Share Imbalance vector summed exactly to zero |

Population accounting reconciles exactly: `17,912 + 741 = 18,653`. No
outcome availability, outcome value, or label affected eligibility.

## 5. Governed measurement

For candidate square `s`, the experiment used the frozen, protocol-published
per-square deployed lamports `D_s` and Miner Count `M_s` from one immutable
decision observation. With board totals `S_D = sum_j(D_j)` and
`S_M = sum_j(M_j)`, Signed Deployment–Miner Share Imbalance was:

```text
I_s = DeploymentShare(s) - MinerShare(s)
    = D_s / S_D - M_s / S_M
    = (D_s * S_M - M_s * S_D) / (S_D * S_M)
```

The measurement is a dimensionless signed share difference. Each value was
represented as a canonical reduced signed rational, with zero uniquely
represented as `0 / 1`. Comparisons and average ranks used exact arithmetic.
The protocol required positive board totals and failed closed otherwise.

The sign recorded only whether a square's Deployment share was above, equal
to, or below its Miner share. It did not classify the square as favorable or
unfavorable.

## 6. Sealed characterization results

All three governed comparisons used the same 17,912 eligible decisions and
the same 25 canonical candidates per decision.

| Comparison | Identical average-rank vectors | Tie-only changes | Strict changes | Mean pairwise disagreement | Mean total rank displacement |
| --- | ---: | ---: | ---: | ---: | ---: |
| Share Imbalance vs Deployment | 0 | 0 | 17,912 | 92.7726 | 134.3306 |
| Share Imbalance vs Miner Count | 0 | 0 | 17,912 | 255.9365 | 289.2788 |
| Share Imbalance vs Deployment per Miner | 8,980 | 0 | 8,932 | 0.7635 | 1.5073 |

Share Imbalance therefore contained strict ordering changes relative to raw
Deployment and Miner Count in every eligible decision. Its relationship with
Deployment per Miner was closer: 8,980 decisions had identical average-rank
vectors and 8,932 had strict changes. No governed comparison produced a
tie-only classification.

Every eligible decision passed the exact zero-sum invariant. Outcome access
was prohibited and was not performed.

## 7. Validity determination

The authoritative execution is historically valid under Research Execution
Specification v2 and `outcome_blind_characterization_v1` because:

- the governing source, protocol, specification, profile, dataset, Replay,
  and experiment identities were bound and reconstructed;
- population dispositions reconciled to all 18,653 Replay rounds;
- all 17,912 eligible decisions had 25 exact signed values and passed the
  zero-sum invariant;
- all three governed comparisons were produced for every eligible decision;
- artifact contracts, canonical encodings, identities, byte counts, record
  counts, and dependencies validated;
- deterministic regeneration was byte-identical and reconstruction was
  `validated`;
- the conformance result was `passed`; and
- the terminal manifest recorded outcome access as
  `prohibited_and_not_performed` with no outcome-aware extension.

## 8. Bounded scientific interpretation

Experiment 2D established that signed Share Imbalance has measurable ordering
structure relative to the previously characterized participant-state
measurements.

Its ordering was empirically distinct from both direct participant-state
orderings throughout the eligible population. It was not algebraically or
empirically identical to Deployment per Miner, although the two relationship
orderings overlapped substantially and had comparatively small aggregate
differences.

This is an ordering-characterization result. The words *different*,
*distinct*, and *measurable* refer only to the sealed rank-vector,
pairwise-divergence, and rank-displacement evidence.

## 9. Historical limitations

- The evidence is bound to the frozen Replay dataset, protocol source
  revision, `end_slot - 5` decision boundary, and complete-lifecycle
  population governed by Experiment 2D.
- The 741 incomplete-lifecycle rounds were excluded prospectively and were
  not repaired or substituted.
- The characterization compared only the three predeclared reference
  orderings.
- The execution was intentionally outcome blind, so it cannot establish any
  relationship between ordering differences and eventual winners.
- The invalid preflight attempt under `3ba070b` supplied no scientific
  evidence; all reported evidence comes from the valid execution under
  `b09400d`.
- This standalone document was reconstructed retrospectively rather than
  authored contemporaneously with the execution.

## 10. What the result does not establish

Experiment 2D did **not** establish:

- predictive value;
- winner-selection superiority;
- profitability or economic advantage;
- Strategy behavior;
- live-deployment suitability;
- superiority of Share Imbalance over Deployment per Miner; or
- authorization for a predictive experiment or decision engine.

No such claim should be inferred from ordering novelty alone.

## 11. Relationship to the participant-state family review

The later Participant-State Family Review was the first repository document
found to use the label **Finding 004**. It explicitly defined that label, for
the purposes of its family-level review, as the result reconstructed from the
valid Experiment 2D artifacts and did not claim that a separate Finding 004
already existed.

That review accurately preserved the principal Experiment 2D comparison
results and used them to assess the maturity of the participant-state signal
family. This retrospective standalone finding now records the same historical
experiment as a discrete archival result. It does not alter, supersede, or
retroactively change the family review.

## 12. Reproducibility and artifact references

The authoritative artifacts are preserved under:

`data/research/analyses/rq003/experiment-002d-share-imbalance-characterization/first-official-b09400d/`

The sealed set contains:

- `experiment_audit_manifest.json`;
- `outcome_blind_provenance.json`;
- `population.json`;
- `derived_measurement.json`;
- `characterization_artifact.jsonl`;
- `ordering_distributions.json`;
- `board_characteristics.json`; and
- `conformance.json`.

The audit-manifest identity, Replay identity, source provenance identity,
protocol digest, dataset digest, execution-specification identity, and profile
identity recorded above are the authoritative bindings for reconstruction.
The invalid earlier attempt must not be substituted for this artifact set.
