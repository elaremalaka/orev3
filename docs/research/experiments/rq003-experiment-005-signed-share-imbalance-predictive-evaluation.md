# RQ-003 Experiment 5 — Signed Share Imbalance Predictive Evaluation

## Status

- Type: Proposed governing research protocol
- Protocol status: Draft for targeted scientific and governance review
- Research design: Complete
- Implementation authorized: No
- Empirical execution authorized: No
- Outcome access authorized: No
- Research Execution Specification:
  [v2](../specifications/rq003-research-execution-specification-v2.md)
- Execution profile: `outcome_aware_v1`

This document prospectively specifies the predictive evaluation of direct
Signed Deployment–Miner Share Imbalance. It fixes the scientific question,
measurement, population, comparison procedures, controls, metrics,
uncertainty, dispositions, and confirmation boundary before any Experiment 5
outcome access.

This draft is not frozen authority. It does not authorize implementation,
outcome access, empirical execution, a production adapter, a projection
contract, a readiness candidate, `READINESS_VALIDATED`, an evidence-
publication commit E, a readiness seal R, `EXECUTION_READY`, Strategy use,
launch activity, or economic interpretation.

## Authority and scientific lineage

This protocol is subordinate to:

- [RQ-003 — Decision-Time Winning-Square Information](../questions/RQ-003-winning-square-predictability.md);
- [RFC-003B Handoff](../../rfcs/RFC-003B-HANDOFF.md);
- [RFC-010 — Strategy Lab](../../rfcs/RFC-010-STRATEGY-LAB.md);
- [RFC-014 — Protocol Revision Provenance](../../../rfcs/RFC-014-PROTOCOL-REVISION-PROVENANCE.md);
- [RQ-003 Research Execution Specification v2](../specifications/rq003-research-execution-specification-v2.md);
- [Finding 001 — Direct Deployment Ordering](../findings/rq003-experiment-001-analysis.md);
- [Finding 002 — Deployment-per-Miner Characterization](../findings/rq003-experiment-002-analysis.md);
- [Finding 003 — Miner Count Characterization](../findings/rq003-experiment-002c-analysis.md);
- [Finding 004 — Signed Share Imbalance Characterization](../findings/rq003-experiment-002d-analysis.md);
- [Finding 005 — Miner Count Predictive Evaluation](../findings/rq003-experiment-003-analysis.md);
- [Finding 006 — Deployment-per-Miner Predictive Evaluation](../findings/rq003-experiment-004-analysis.md);
- the [RQ-003 Signal Discovery Roadmap](../investigations/rq003-signal-discovery-roadmap.md);
- the [RQ-003 Predictive Evaluation Roadmap](../investigations/rq003-predictive-evaluation-roadmap.md);
- the [RQ-003 Minimum-Effect Scope Clarification v1](../governance/rq003-minimum-effect-scope-clarification-v1.md); and
- the [Execution Readiness completion checkpoint](../../project-checkpoints/ore-v3-execution-readiness-comprehensive-completion.md).

The validated [Experiment 3](rq003-experiment-003-miner-count-predictive-evaluation.md)
and [Experiment 4](rq003-experiment-004-deployment-per-miner-predictive-evaluation.md)
protocols supply the predictive-evaluation framework. This protocol reuses
their decision boundary, population construction, permanent uninformed
baselines, tie convention, chronology controls, primary metric, moving-block
bootstrap, and interpretation limits. It changes the governed measurement,
adds one fixed-sequence paired comparison with Deployment per Miner, and
separates bounded initial support from the later disjoint confirmation needed
for an RQ-003 alternative-supported conclusion.

Finding 004 established outcome-blindly that Share Imbalance is not an
empirical duplicate of Deployment per Miner, although the two orderings
overlap substantially. Finding 006 is valid negative evidence for direct
descending Deployment per Miner at the same tested decision point. Neither
finding answers the predictive question in this protocol. Structural novelty
does not imply predictive value, and a negative comparator does not make
incremental improvement easier to claim.

## 1. Scientific questions

### 1.1 Primary direct question

Does direct descending exact Signed Deployment–Miner Share Imbalance provide
reproducible winner-ranking information over both permanent uninformed
baselines under the established RQ-003 methodology?

### 1.2 Secondary gated question

Only if the primary direct family satisfies every initial-support requirement,
does descending exact Share Imbalance produce a positive paired reciprocal-
rank improvement over descending exact Deployment per Miner on the identical
eligible labeled population?

The secondary question is a ranking-quality contrast between two fixed direct
procedures. It does not estimate conditional mutual information, causal
independence, learned-model incremental value, Strategy value, profitability,
or economic materiality.

### 1.3 Hypotheses

For the primary family, the null is not rejected unless Share-Imbalance MRR
has a positive reproducible paired difference against both uninformed
baselines under every required control. The bounded initial alternative is
provisional support for later disjoint confirmation, not final RQ-003
`alternative_supported` authority.

For the gated secondary comparison, positive paired ranking-quality
improvement is supported only when the fixed two-sided paired interval has a
lower bound greater than zero. Failure to establish that contrast does not
change a valid primary disposition.

## 2. Governed measurement

### 2.1 Inputs and board totals

For candidate square `s` in one immutable decision snapshot, let:

- `D_s` be the protocol-published non-negative deployed lamports;
- `M_s` be the protocol-published non-negative per-square Miner Count;
- `S_D = sum_j(D_j)` over the 25 canonical squares; and
- `S_M = sum_j(M_j)` over the 25 canonical squares.

`S_M` is summed per-square membership, not the round-wide unique-miner
aggregate. All values must originate from the same frozen decision snapshot
and must reconstruct through their approved fundamental-measurement metadata,
context views, executable bindings, deterministic pipeline, and immutable
`MeasurementVector` authority.

### 2.2 Exact Signed Share Imbalance

Define:

```text
DeploymentShare(s) = D_s / S_D
MinerShare(s)      = M_s / S_M

I_s = D_s / S_D - M_s / S_M
    = (D_s * S_M - M_s * S_D) / (S_D * S_M)
```

`I_s` is a dimensionless signed share difference:

- `I_s > 0` means Deployment share exceeds Miner share;
- `I_s = 0` means the shares are equal; and
- `I_s < 0` means Deployment share is below Miner share.

The sign controls the predeclared ordering only. It is not a favorable class,
probability, prediction, recommendation, or economic interpretation.

### 2.3 Zero and conformance rules

The rules are exhaustive:

- `S_D > 0` and `S_M > 0` are mandatory;
- a zero board total fails measurement conformance closed before ranking;
- candidate-level `D_s = 0`, `M_s = 0`, or both are valid when both totals
  remain positive; and
- no pseudocount, smoothing, imputation, clipping, standardization, absolute-
  value transform, learned transform, or other replacement is permitted.

No alternate observation may repair a failed measurement. Outcome presence,
value, provenance, or availability cannot affect conformance.

### 2.4 Canonical exact representation

Represent every `I_s` as a reduced signed rational pair:

```text
signed_numerator = D_s * S_M - M_s * S_D
positive_denominator = S_D * S_M
```

Divide both by
`gcd(abs(signed_numerator), positive_denominator)`. Canonical zero is exactly
`0 / 1`. Comparisons use signed integer cross multiplication. Floating-point
division, rounding, approximate equality, and candidate-identity tie-breaking
are prohibited.

The common positive denominator permits an implementation to compare signed
numerators within one decision, but the canonical persisted measurement and
identity material remain the reduced signed rational.

### 2.5 Experiment Feature Set

The experiment-local Feature Set contains exactly one scalar concept:

| Position | Field | Source | Transformation |
| ---: | --- | --- | --- |
| 1 | `signed_deployment_miner_share_imbalance` | Canonical exact derived measurement | None |

It contains no outcome, raw Deployment feature, Miner Count feature,
Deployment-per-Miner feature, historical input, audit variable, or additional
derived measurement. The separately governed Deployment-per-Miner procedure
is a scientific comparator, not a second field in this Feature Set.

## 3. Procedures, ordering, and ties

Every eligible decision constructs exactly these required procedures over the
same 25 canonical candidates:

1. descending exact Signed Share Imbalance — primary experimental procedure;
2. ascending canonical square identifier — deterministic uninformed baseline;
3. deterministic seeded-random permutation — uninformed baseline; and
4. descending exact Deployment per Miner — paired scientific comparator.

Raw Deployment and direct Miner Count remain frozen contextual findings. They
are not additional Experiment 5 predictive baseline families and must not be
added after outcome access.

### 3.1 Primary ordering

Order candidates by descending exact `I_s`. No secondary key, learned
parameter, scaling, candidate adjustment, or additional measurement is
permitted.

Equal exact rationals form a measurement tie. Every candidate in a tie group
receives the arithmetic mean of its occupied one-based positions. Candidate
identity must not break a measurement tie. Top-k is a hit exactly when the
winner's average rank is at most `k`.

### 3.2 Permanent uninformed baselines

The deterministic baseline orders candidates by ascending canonical square
identifier and consumes no measurement, outcome, chronology, or protocol
state.

The seeded-random baseline reuses the exact Experiment 3/4 deterministic
SHA-256 construction, changing only the prospectively fixed domain separator.
Its decision identity is the lowercase 64-hex
`RQ003ExecutionContext.decision_snapshot_identity` shared by all 25 candidate
contexts at the selected observation. For each candidate square, represented
as the JSON integer `0` through `24`, construct exactly:

```json
{
  "candidate_square": <square>,
  "decision_identity": <decision_snapshot_identity>,
  "domain": "rq003-experiment-005-seeded-random-v1"
}
```

Encode that object with the frozen
`orev3.features.rq003_contracts.canonical_encode` version-1 semantics: wrap it
as `{"canonical_encoding_version":1,"value":<canonical-value>}`, serialize
UTF-8 JSON with object keys sorted lexicographically, no insignificant
whitespace, `ensure_ascii=false`, and non-finite numbers prohibited. Hash the
exact bytes with SHA-256 and retain the complete 32 digest bytes.

The experiment-specific domain is therefore exactly:

```text
rq003-experiment-005-seeded-random-v1
```

Order candidates by their 32-byte digests in ascending unsigned lexicographic
byte order. If any two candidates have equal digests, the decision fails
closed; candidate identity must not break the collision. Assign integer rank
`1` to the first digest through rank `25` to the last, then store each rank at
its candidate-square position. This is a strict permutation, so average-rank
tie handling is inapplicable to this baseline.

The construction receives no measurement, outcome, outcome provenance,
protocol revision, timestamp, dataset location, ambient PRNG state, or runtime
randomness. The same decision identity and ranking population used by the
primary procedure are mandatory. No alternate encoding, digest subset,
ordering direction, seed, or favorable permutation may be selected later.

### 3.3 Deployment-per-Miner comparator

The comparator is descending exact `D_s / M_s` under the complete governed
measurement, zero, rational, and average-rank semantics of Experiment 4. It
uses the same immutable `D_s` and `M_s` values as Share Imbalance. It is not
redefined from the Experiment 4 result, and the historical Experiment 4
artifacts are contextual evidence rather than substitutes for the paired
Experiment 5 computation on the Experiment 5 population.

### 3.4 Ascending sensitivity

Ascending exact Share Imbalance is the sole predeclared direction sensitivity.
It uses the same exact values and average-rank convention. It is non-rescuing:
it cannot satisfy a primary or incremental criterion, change a disposition,
select a subgroup, or become a Strategy procedure from this experiment.

### 3.5 Procedure parity

The primary, both baselines, and the Deployment-per-Miner comparator must use:

- identical decisions and 25-candidate sets;
- identical ranked and labeled evaluation populations;
- identical winner-rank, fold, stratum, and uncertainty definitions; and
- the same authorized outcome source and provenance rules.

Any procedure-specific omission or population substitution invalidates the
affected execution rather than creating an unpaired comparison.

## 4. Initial population, chronology, and outcome boundary

### 4.1 Immutable initial dataset

The bounded initial evaluation uses:

- dataset version `replay-dataset-v1`;
- persisted dataset SHA-256
  `7680856bc6a01f9b69be0921d6e66b3f43d5241a38e63b37871b6925c1d59ba7`;
- the derived Replay identity reconstructed from first-order bindings;
- one homogeneous supported RFC-014 protocol-revision population; and
- Research Execution Specification v2 profile `outcome_aware_v1`.

A byte-different dataset, different logical source, pooled revision,
different decision point, or different population is a new prospective
protocol revision and cannot be substituted silently.

### 4.2 Decision selection and ordering

Select one decision per Replay round: the latest valid normal observation at
or before `end_slot - 5`. If none exists, exclude the round before ranking
with disposition `no_predeclared_decision_observation`. A measurement-
nonconformant decision receives one deterministic pre-outcome conformance
disposition. Do not choose another observation using outcome knowledge.

Order Replay rounds by ascending immutable chronology with `round_id` as the
deterministic tie-breaker. Candidate squares are canonically `0` through `24`.
Keep all candidates from one round together.

### 4.3 Pre-outcome ranking population

A round enters the ranking population only if:

1. its Replay lifecycle has one recognized complete or partial disposition,
   recorded as audit metadata but not used as a ranking input;
2. its predeclared decision observation is valid;
3. both fundamental measurements reconstruct and conform for all 25
   candidates;
4. `S_D > 0` and `S_M > 0`;
5. Share Imbalance and Deployment per Miner reconstruct exactly;
6. all four required procedures cover the identical 25 candidates; and
7. the bound protocol revision is supported and homogeneous.

Eligibility and every pre-ranking exclusion are frozen before outcome access.
Outcome availability must not change membership.

### 4.4 Outcome-blind freeze and authorized join

Execution order is:

```text
Replay decision state
  -> frozen DecisionContext
  -> immutable RQ003ExecutionContext
  -> fundamental MeasurementVectors
  -> exact Share Imbalance and Deployment-per-Miner measurements
  -> one-scalar Experiment 5 Feature Set
  -> all procedure rankings
  -> frozen outcome-blind ranking artifact
  -> authorized outcome join
  -> evaluation
```

Before outcome access, freeze and validate population dispositions, first-
order authority, every exact measurement, procedure identity, rank, tie,
artifact declaration, ranking artifact, and outcome-blind provenance block.
The ranking artifact contains no label, winner, outcome availability, capture
mode, or outcome provenance.

Only after reconstruction succeeds may `outcome_aware_v1` authorize the
declared outcome source. No outcome may alter decision selection, exclusions,
values, ties, ranks, procedures, or population membership.

### 4.5 Outcome provenance and missingness

Permitted valid provenance is exactly:

- `current_round`;
- `post_transition_predecessor`; and
- `enriched` under the declared immutable outcome-source contract.

Ambiguous, conflicting, invalid, or legacy-unspecified labels are rejected
under Research Execution Specification v2. Missing labels remain explicit,
are never imputed or inferred, and are not counted as misses.

Population accounting must reconcile exactly:

- the complete Replay population;
- pre-ranking exclusions by one deterministic reason;
- ranked decisions;
- valid labels and missing labels;
- complete-lifecycle primary evaluations; and
- separately reported sensitivity populations.

Outcome provenance is evaluation metadata only and may not enter ranking or
pre-outcome eligibility.

### 4.6 Primary labeled population and support

A ranked round enters the primary evaluation only when it has a complete
Replay lifecycle and exactly one valid finalized winning-square label joined
after ranking freeze.

Sort primary rounds chronologically and divide them into five consecutive
folds. Let `q, r = divmod(N, 5)`: the first `r` folds contain `q + 1` rounds
and the remaining folds contain `q` rounds. Counts therefore differ by at
most one without an implementation-selected remainder rule. A fold or control
stratum is inferentially adequate at `N >= 100`. Every fold must be adequate
for any favorable initial disposition. Therefore fewer than 500 primary-
eligible labeled rounds is `evidence_insufficient`.

Groups below 100 are descriptive only and do not determine favorable or
negative inference. Random row-, candidate-, observation-, or round-level
splits are prohibited.

## 5. Controls

### 5.1 Information-flow and leakage control

- Freeze normal decision snapshots before RFC-012 outcome evidence is opened.
- Permit only the two approved fundamental measurements and their two exact
  governed derivations as procedure inputs.
- Exclude winners, finalized values, future observations, outcome
  availability, capture mode, enrichment, and replay internals from ranking.
- Freeze all rankings before authorized outcome access.
- Verify that outcome attachment changes no ranking identity.

Any violation makes the execution `invalid_execution`.

### 5.2 Chronology and revision control

Preserve ascending round chronology in selection, folds, resampling, and
reporting. Protocol revision is immutable validation provenance only and may
not enter values, ties, or ranking. Unsupported or semantically incompatible
revisions are reported separately and never pooled.

### 5.3 Observation-count and decision-distance control

Report exact normal-observation-count frequency maps for all Replay-bound
rounds, ranked decisions, primary labeled rounds, ranked rounds missing only
an outcome, and each pre-ranking exclusion reason. Every map must reconcile
with its population.

For each ranked decision define:

```text
decision_distance_slots = (end_slot - 5) - selected_observation_slot
```

Report the predeclared `0`, `1`, `2`, and `3+` strata for ranked and primary
populations and report primary paired metrics in every adequate stratum.
Distance, observation count, wall-clock spacing, and collector cadence are
audit variables only.

### 5.4 Lifecycle and provenance controls

Complete lifecycles alone form the primary population. Otherwise valid
partial-start, partial-end, and partial-both labeled rounds form a separate
predeclared lifecycle sensitivity and cannot rescue the primary result.

Report paired primary metrics for every permitted outcome-provenance group
with adequate support. Provenance diversity is not an end in itself and no
minimum count of distinct provenance groups is imposed:

- with zero adequately supported provenance groups, provenance robustness
  cannot be assessed and the primary evidence is `evidence_insufficient`;
- with exactly one adequately supported provenance group, positive paired
  differences against both uninformed baselines in that group satisfy this
  control, provided the aggregate primary family also passes; the conclusion
  must be scoped to that homogeneous provenance and may not claim cross-
  provenance robustness;
- with two or more adequately supported provenance groups, positive paired
  differences against both baselines are required in every supported group;
  any supported conflicting group produces `null_not_rejected`; and
- groups below 100 are descriptive only and cannot rescue or defeat the
  primary family or be used to infer heterogeneity.

This distinguishes absent support for a robustness assessment from actual
contradictory evidence and from internally valid homogeneous-provenance
capture. No unfavorable adequately supported provenance group may be hidden,
pooled away, or replaced.

### 5.5 Decision-neutral missingness comparability

After the outcome-blind ranking population is frozen, partition it exactly
into rounds with one valid authorized label and rounds missing only that
label. Produce side-by-side count and proportion tables for those two
populations using only pre-outcome or audit metadata:

1. the five consecutive chronological partitions obtained by applying the
   Section 4.6 `q, r = divmod(N, 5)` rule to the complete ranked population;
2. normal `observation_count`, `significant_gap_count`, and
   `max_observation_gap_seconds`, plus the predeclared decision-distance
   strata `0`, `1`, `2`, and `3+`;
3. cadence regime `no_significant_gap` when `significant_gap_count = 0` and
   `significant_gap_present` when it is positive, under the persisted
   `significant_gap_threshold_seconds`;
4. lifecycle coverage `complete`, `partial_start`, `partial_end`, and
   `partial_both`; and
5. the exact collector regime defined below.

The authoritative collector-regime key for one round is the version-1
canonical encoding of exactly:

```json
{
  "collector_session_ids": [<ascending UTF-8 session identities>],
  "source_schema_versions": [<ascending integer schema versions>]
}
```

Both arrays are duplicate-free and retain every value from the immutable
lifecycle. `collector_session_count` must equal the length of
`collector_session_ids`; report it as a reconciliation field but do not use it
in place of the identities. A round spanning multiple sessions has the one
ordered multi-session key above. Different session-identity sets are distinct
regimes even when their counts and schema versions match. This prevents
scientifically distinct collection intervals from being pooled merely because
they used the same schema.

Order table categories as follows: chronological partitions `1` through `5`;
integer observation counts ascending; integer significant-gap counts
ascending; finite nonnegative maximum gaps by ascending binary64 numeric value;
decision distance `0`, `1`, `2`, `3+`; cadence regime
`no_significant_gap`, `significant_gap_present`; lifecycle `complete`,
`partial_start`, `partial_end`, `partial_both`; and collector-regime keys by
ascending version-1 canonical-encoded bytes. Report comparison dimensions in
the numbered order above.

Every lifecycle must carry a finite nonnegative maximum gap, a nonnegative
integer significant-gap count, and a finite nonnegative persisted significant-
gap threshold. The threshold must be homogeneous for pooled cadence reporting;
otherwise report each threshold separately and classify comparability as not
assessable until one prospectively governed threshold population is selected.
Observation-count and exact-gap frequency maps are required diagnostics. The
five chronology partitions, four decision-distance strata, two cadence
regimes, four lifecycle states, and exact collector regimes are the principal
comparability strata.

Each table must report labeled count, missing count, stratum total, labeled
proportion, and missing proportion; stratum total is exactly labeled count
plus missing count, and all totals must reconcile to the frozen ranking
population. Represent proportions as reduced nonnegative rational
values: labeled proportion is `labeled_stratum_count / total_labeled_count`
and missing proportion is `missing_stratum_count / total_missing_count`. When
either comparison population is empty, its complete proportion vector is
`not_available` rather than zero. Compare
the labeled and missing proportion vectors over the union of their ordered
categories, inserting an exact zero count for an absent category. The vectors
differ if any corresponding reduced rational differs. No winner identity,
rank quality, procedure metric, or post-join performance enters this audit.
Missing labels remain missing; the audit neither imputes them nor treats them
as losses.

If the missing population is empty, record `complete_outcome_coverage` and no
comparability warning is required. If the labeled population is empty, the
mandatory primary support is absent and the result is
`evidence_insufficient`; no distributional comparison is inferred from an
empty population.

Invalid or internally inconsistent chronology, decision-distance, lifecycle,
gap, or collector metadata is a protocol/data-conformance failure and produces
`invalid_execution`. A schema-valid empty collector-session list or otherwise
legitimately unavailable session identity is not fabricated: record its rounds
under `collector_regime_metadata_unavailable`. It is structurally valid but
cannot establish collector-regime comparability.

Assign exactly one comparability state in this precedence:

1. `comparability_not_assessable` when required schema-valid metadata is
   unavailable for 100 or more ranked rounds, cadence thresholds cannot form
   one governed population, or no collector regime containing at least 100
   ranked rounds has adequate labeled support;
2. `material_comparability_failure` when any principal stratum containing at
   least 100 ranked rounds has fewer than 100 valid labels, so the direction
   cannot be assessed with the same governed adequacy standard;
3. `generalization_warning` when all principal ranking-supported strata have
   adequate labeled support and the audit is assessable, but one or more exact
   labeled-versus-missing proportion vectors differ; or
4. `comparable_for_bounded_labeled_inference` when the audit is assessable,
   all principal ranking-supported strata have adequate labeled support, and
   every exact proportion vector is equal. Complete outcome coverage also
   records this state without requiring a missing-population vector.

For this rule, a principal stratum is ranking-supported when it contains at
least 100 ranked rounds and label-supported when it contains at least 100
valid labeled rounds. Strata below 100 ranked rounds remain descriptive and
cannot create a failure or rescue another state. The lack of a second
collector regime is not insufficient: one homogeneous regime passes when it
is metadata-complete and label-supported.

For every label-supported principal stratum, report both direct paired MRR
differences under the same population-parity rules as the primary family.
These stratum metrics are controls only: agreement cannot rescue aggregate
failure. A supported performance conflict is evaluated separately as bounded
negative stability evidence under Section 9.5; it does not change the
comparability state derived from label coverage and metadata.

Protocol/data-integrity failure remains `invalid_execution`. Otherwise,
`comparability_not_assessable` and `material_comparability_failure` map to
`evidence_insufficient`; `generalization_warning` and
`comparable_for_bounded_labeled_inference` permit primary evaluation to
continue. An observable proportion difference alone is therefore a warning,
not invalidity or negative predictive evidence.

No provisional disposition may be generalized to all Replay rounds while any
ranked outcomes are missing. Under `generalization_warning`, any provisional
conclusion is explicitly qualified as applying to the supported labeled
population and must identify the differing dimensions. Under either
insufficient state, provisional support is prohibited even if aggregate
performance is favorable.

This audit detects limits on generalization; it does not turn an observable
distribution difference into an outcome-tuned exclusion or allow a favorable
subpopulation to rescue the aggregate primary family.

### 5.6 Evaluation-bias control

Before outcome access freeze the signal definition, direction, exact
arithmetic, zero and tie rules, procedures, seed domains, decision point,
population, chronology, folds, metrics, uncertainty, support threshold,
exclusions, dispositions, materiality interpretation, and confirmation rule.

Report every required endpoint and sensitivity, including unfavorable
results. No ascending result, Deployment-per-Miner comparison, subgroup,
secondary endpoint, diagnostic, or sensitivity may rescue a failed primary
criterion.

## 6. Estimands and metrics

### 6.1 Primary estimands

On the identical primary population, the two co-primary estimands are:

```text
MRR(descending Share Imbalance) - MRR(deterministic baseline)

MRR(descending Share Imbalance) - MRR(seeded-random baseline)
```

Mean Reciprocal Rank is:

```text
MRR = (1 / N) * sum_r(1 / winner_rank_r)
```

The round is the independent unit. `winner_rank_r` is the finalized winner's
one-based average rank. MRR is ranking quality, not probability, reward,
profitability, or economic value.

### 6.2 Gated incremental estimand

The sole incremental estimand is:

```text
MRR(descending Share Imbalance)
  - MRR(descending Deployment per Miner)
```

It uses the identical eligible labeled rounds and candidate population. It is
inferentially tested only after every direct primary initial-support criterion
passes. Closing the gate does not suppress descriptive reporting, but no
incremental-support conclusion may then be drawn.

### 6.3 Secondary and diagnostic metrics

Report without replacing the primary estimands:

- winner rank for every primary round;
- mean and median winner rank;
- complete winner-rank distribution;
- Top-1, Top-3, and Top-5 hit rates;
- exact-tie frequency and tie-group distributions;
- winning-square tie frequency and winning tie-group size;
- all primary and incremental metrics by chronological fold;
- decision-distance, lifecycle, and outcome-provenance sensitivities; and
- ascending Share-Imbalance sensitivity metrics.

No secondary metric enters a disposition.

## 7. Uncertainty and fixed-sequence inference

Use the exact Experiment 3/4 deterministic circular moving-block bootstrap
defined below. The round is the independent unit. Let the `N` primary
evaluation rounds be in the canonical chronological order from Section 4.6.
For each comparator `c`, construct the paired vector in that order:

```text
x_c[r] = reciprocal_rank_share_imbalance[r]
         - reciprocal_rank_c[r]
```

The comparator set is deterministic baseline, seeded-random baseline, and
Deployment per Miner. The same ordered rounds and one shared resampling
schedule apply to all three vectors.

### 7.1 Normative binary64 path

Experiment 005 binds the exact numeric semantics used by the frozen Experiment
3 and Experiment 4 implementations. `binary64` means IEEE 754 binary64 with
round-to-nearest, ties-to-even after every normative operation. Implementations
must not retain wider intermediate precision, contract operations, use a fused
operation, reassociate expressions, or convert through a decimal approximation
when doing so could change a binary64 result.

Construct the numeric path in this order:

1. An average winner rank is `((first_position + last_position) / 2)` after
   integer addition. All permitted integer and half-integer ranks from `1`
   through `25` are represented exactly as binary64. Strict baseline ranks are
   converted exactly from their integers.
2. Compute each reciprocal rank as the binary64 division `1.0 / rank`, rounded
   immediately to binary64.
3. Construct each paired value as one binary64 subtraction in the displayed
   Section 7 order: rounded Share-Imbalance reciprocal rank minus rounded
   comparator reciprocal rank. Round the subtraction immediately to binary64.
   Do not subtract exact rational reciprocals and convert only afterward.
4. For an observed MRR or observed paired MRR difference, treat the already-
   rounded binary64 operands as their exact represented values, sum those
   values exactly, divide the exact sum by the integer count, and round the
   quotient once to binary64. This is the `statistics.mean` behavior bound by
   Experiments 3 and 4.
5. Bootstrap prefix, block, replicate, and percentile operations then follow
   Sections 7.3 and 7.4, with every displayed addition, subtraction,
   multiplication, and division rounded to binary64 before the next operation.

Normalize every numeric zero emitted into canonical material to positive
binary64 `+0.0`. NaN, infinities, negative zero in canonical output, alternate
rounding modes, platform extended precision, and mathematically equivalent but
differently associated evaluation are prohibited.

For the inherited primary interval construction, convert the decimal confidence
literal `0.975` directly to its nearest binary64 value under round-to-nearest,
ties-to-even. Let `one` be binary64 `1.0` and `two` be binary64 `2.0`, then
evaluate exactly in this order:

```text
primary_confidence = binary64(0.975)
primary_tail = (one - primary_confidence) / two
primary_lower_probability = primary_tail
primary_upper_probability = one - primary_tail
```

Round the subtraction, division, and final subtraction immediately to binary64
under round-to-nearest, ties-to-even. These operation-derived probabilities,
not direct binary64 conversions of the mathematically equivalent decimal tails
or endpoints, are the probabilities supplied to Type-7 interpolation. This is
the exact construction used by the frozen Experiment 3 and Experiment 4
implementations.

The 95% Deployment-per-Miner interval is an Experiment 005 prospective
extension using the same inherited construction pattern; Experiments 3 and 4
did not define this secondary interval. Convert the decimal confidence literal
`0.95` directly to binary64, then evaluate exactly:

```text
secondary_confidence = binary64(0.95)
secondary_tail = (one - secondary_confidence) / two
secondary_lower_probability = secondary_tail
secondary_upper_probability = one - secondary_tail
```

Apply the same immediate binary64 rounding after each displayed operation.
These requirements govern metrics, paired vectors, replicate statistics,
interval endpoints, and every conclusion comparison with zero.

### 7.2 Block and start construction

Let `L` be the smallest positive integer such that `L^3 >= N`, which is
`ceil(N^(1/3))`. Let `K = ceil(N / L)`. The bootstrap has exactly 10,000
replicates numbered `0` through `9,999`. Within every replicate, block indices
restart at `0` and run through `K - 1`.

For replicate `replicate` and block `block_index`, construct exactly:

```json
{
  "block_index": <block_index>,
  "domain": "rq003-experiment-005-moving-block-bootstrap-v1",
  "replicate": <replicate>
}
```

Encode this object with the exact version-1 `canonical_encode` semantics in
Section 3.2 and hash it with SHA-256. Interpret the first eight digest bytes as
one unsigned 64-bit big-endian integer and set:

```text
start = integer mod N
```

No later digest byte, rejection sampling, PRNG, mutable counter, experiment
result, or comparator-specific state enters the start. The replicate and
block indices are the complete counters and reset only as specified above.

### 7.3 Circular sampling and replicate statistic

For a block starting at `start`, append values in forward chronological-vector
order:

```text
x_c[(start + 0) mod N], x_c[(start + 1) mod N], ...
```

Equivalently, concatenate `x_c` with itself and take one consecutive block.
Use length `L` for each block except that the final block is truncated to the
number of values still required. Concatenate blocks in increasing
`block_index` order. Every replicate therefore contains exactly `N` values;
overrun, padding, or a shorter resample fails reconstruction.

For each comparator vector, first form the doubled vector `d = x_c + x_c` and
the binary64 prefix array `p` exactly as:

```text
p[0] = 0.0
p[i + 1] = p[i] + d[i]        for i ascending from 0
```

The sum for a block is exactly `p[start + length] - p[start]`. Initialize the
replicate sum to `0.0`, add those block sums in increasing `block_index` order,
and divide the final sum by `N`. This is the exact prefix-sum evaluation order
used by the frozen Experiment 3/4 implementation; it is not interchangeable
with summing the sampled values individually or reassociating additions.

Reuse the same start and length sequence for all three comparators.
Comparator-specific resampling or a separately generated secondary schedule
is prohibited. The replicate statistic is therefore the declared binary64
arithmetic mean of exactly `N` resampled paired differences.

### 7.4 Exact percentile rule

For each comparator, sort its 10,000 replicate statistics in nondecreasing
numeric order as `v[0]` through `v[9,999]`. For probability `p` in `[0,1]`,
use the frozen linear percentile rule:

```text
h = (B - 1) * p, where B = 10,000
j = floor(h)
k = ceil(h)
w = h - j

percentile(p) = v[j]                          when j = k
percentile(p) = v[j] * (1 - w) + v[k] * w    otherwise
```

This is the Type-7-style interpolation used by Experiments 3 and 4. At
`p = 0` or `p = 1`, it returns the first or last sorted statistic exactly.
Non-finite values are prohibited. The interpolation operations use binary64
in the displayed order, matching the frozen implementation.

For each primary comparison, the two-sided 97.5% percentile interval is:

```text
[percentile(primary_lower_probability),
 percentile(primary_upper_probability)]
```

The two intervals provide Bonferroni family-wise error control at 0.05. Both
primary lower bounds must be greater than zero.

The Deployment-per-Miner comparison is fixed-sequence secondary inference.
Only after the direct primary family passes, its prospectively fixed two-sided
95% paired interval is:

```text
[percentile(secondary_lower_probability),
 percentile(secondary_upper_probability)]
```

A lower bound greater than zero supports positive paired ranking-quality
improvement. Otherwise improvement is not established. The estimate and
interval remain reportable descriptively when the gate is closed, with gate
status explicit.

Freeze the ordered round identities, all three paired vectors, `N`, `L`, `K`,
domain, replicate count, shared start schedule, replicate statistics,
bootstrap identity, and interval outputs. Replicate outputs are generated only
after the authorized outcome join. If reconstruction differs or this declared
method cannot be formed, do not substitute another bootstrap, percentile
rule, asymptotic test, independent-round method, or threshold.

## 8. Materiality and bounded interpretation

Under the prospectively governed
[Minimum-Effect Scope Clarification v1](../governance/rq003-minimum-effect-scope-clarification-v1.md),
no separate positive numeric materiality threshold or `delta_min` is part of
this direct-information protocol. The primary RQ-003 question asks whether the
fixed ordering contains reproducible winner-ranking information beyond both
uninformed baselines. Its prospectively fixed zero-improvement null boundary,
effect estimates, adjusted intervals, stability controls, and disjoint-
confirmation requirement answer only that bounded information question.

Effect estimates and intervals must be reported in full. Statistical support
must not be described as material superiority, practical importance,
profitability, or Strategy suitability. This protocol does not import a
numeric value from a proposal, prior experiment, observed result, detectable-
effect calculation, or sample-size convenience. Any future claim of material
incremental superiority to Deployment per Miner requires separate prospective
governance before outcome access.

The tracked minimum-effect policy remains controlling for a characterization-
to-dependent-evaluation promotion gate such as Experiment 2A to Experiment 2B.
Experiment 005 does not retroactively pass, waive, or reinterpret that gate.
Its gated Deployment-per-Miner contrast asks only whether positive paired
ranking-quality improvement is established; it cannot claim material
incremental superiority. Any such material claim, and every later Strategy,
economic, paper, launch, safety, or capital decision, requires its own
prospectively justified materiality and authority gate.

## 9. Initial dispositions

A completed initial execution applies the following precedence and records
exactly one primary disposition:

1. `invalid_execution` — a structural, protocol, authority, information-flow,
   conformance, reconstruction, or population-parity failure means no valid
   scientific inference exists;
2. `evidence_insufficient` — execution is structurally valid, but mandatory
   population, label, fold, control, or uncertainty support for the bounded
   question is unavailable;
3. `null_not_rejected` — execution is valid and sufficiently informative, but
   one or more required direct primary predictive or stability criteria fail;
   or
4. `provisional_support_for_confirmation` — every required direct primary
   criterion passes.

Evaluate the cases in that order; the first applicable disposition is final.
Later evidence cannot replace an earlier applicable disposition. An invalid
execution has the recorded validity disposition `invalid_execution` but no
scientific positive, negative, or insufficient interpretation.

The archived interval cannot produce final `alternative_supported` authority.

### 9.1 Provisional support for confirmation

`provisional_support_for_confirmation` requires all of:

1. Share-Imbalance MRR is greater than both uninformed baselines on the
   identical primary population;
2. both adjusted 97.5% lower bounds are greater than zero;
3. paired differences against both baselines are positive in every one of
   five adequately supported chronological folds;
4. every required control family has the determinate passing result specified
   in Section 9.5;
5. deterministic reconstruction and regeneration pass;
6. every leakage, conformance, chronology, revision, cadence, lifecycle,
   provenance, missingness, population, and evaluation-bias control passes;
   and
7. the interpretation is limited to the supported initial population and is
   explicitly provisional pending disjoint confirmation.

No sensitivity, Deployment-per-Miner contrast, subgroup, secondary metric,
or diagnostic may replace any item.

### 9.2 Null not rejected

`null_not_rejected` applies when execution is valid and adequately supported
but any direct primary condition fails, including:

- MRR is not higher than either uninformed baseline;
- either adjusted interval includes or falls below zero;
- only one baseline comparison is favorable;
- any adequate chronological fold fails the positive direction against both
  baselines;
- a favorable result exists only in an ascending sensitivity, subgroup,
  comparator, or secondary endpoint; or
- an adequately supported required control demonstrates lack of stability.

This is bounded negative evidence for the exact direct Share-Imbalance
procedure, decision boundary, population, and protocol revision. It does not
prove that every participant-state relationship or future governed procedure
is uninformative.

### 9.3 Evidence insufficient

`evidence_insufficient` applies when execution is valid but the primary
question cannot receive a justified favorable or bounded negative disposition
because of inadequate eligible labels, fewer than five 100-round folds,
inadequate required control support,
or inability to form the predeclared uncertainty construction without an
invalidity defect.

Preserve all valid artifacts and name each unmet requirement. Do not weaken a
threshold, change a population, or convert insufficiency post hoc.

### 9.4 Invalid execution

`invalid_execution` supplies no scientific evidence. It applies when a
required authority, identity, information-flow, population, arithmetic,
procedure, artifact, reconstruction, or protocol-conformance rule fails.
Invalid and valid executions may not be combined.

Population parity is a protocol invariant: any difference among the decisions,
candidate sets, joined labels, or paired round identities used by required
procedures is `invalid_execution`, never `evidence_insufficient`.

### 9.5 Deterministic control-family outcomes

For decision-distance, lifecycle, and provenance performance strata, a
supported stratum agrees with the required direct direction only when both of
its Share-Imbalance paired MRR differences against the uninformed baselines
are strictly positive. A supported stratum that fails either comparison is a
conflict. Unsupported strata are always descriptive and non-rescuing.

The five control families close as follows:

1. **Chronological folds.** Invalid/unavailable chronology is
   `invalid_execution`. Exactly five consecutive folds must be constructible.
   Zero through four adequately supported folds is `evidence_insufficient`;
   the protocol has no valid one-, two-, three-, or four-fold substitute. With
   all five adequate, any conflicting fold is `null_not_rejected`; agreement
   in all five passes this control.
2. **Decision distance.** Invalid or unavailable authoritative distance
   metadata is `invalid_execution`. Zero adequate strata is
   `evidence_insufficient`. Exactly one adequate stratum may pass when it
   agrees, but the conclusion is scoped to that supported distance and makes
   no cross-distance robustness claim. With multiple adequate strata, every
   one must agree; any conflict is `null_not_rejected`.
3. **Lifecycle.** Invalid or unavailable authoritative lifecycle metadata is
   `invalid_execution`. The complete-lifecycle primary population must itself
   supply the five adequate folds; otherwise evidence is insufficient. The
   partial-start, partial-end, and partial-both populations are non-rescuing
   sensitivities: zero adequate partial strata is permissible, exactly one is
   reported on its own, and multiple are reported separately. Any supported
   partial stratum conflicting with an otherwise favorable primary result is
   `null_not_rejected`; agreement never substitutes for failure of the
   complete-lifecycle primary family.
4. **Outcome provenance.** Apply Section 5.4 exactly. Invalid/unavailable
   required provenance metadata is `invalid_execution`; zero adequate groups
   is `evidence_insufficient`; exactly one agreeing group may pass with a
   homogeneous-provenance limitation; with multiple adequate groups, all must
   agree and any conflict is `null_not_rejected`.
5. **Missingness comparability.** This audit compares the complete labeled and
   missing partitions under Section 5.5. Malformed or contradictory required
   metadata is `invalid_execution`. `comparability_not_assessable` and
   `material_comparability_failure` are `evidence_insufficient`.
   `generalization_warning` passes this control only for the explicitly
   bounded labeled-population estimand and requires its qualification;
   `comparable_for_bounded_labeled_inference` passes without that warning.
   One homogeneous, metadata-complete, label-supported collector regime is
   sufficient. After comparability passes, any label-supported cadence or
   collector-regime stratum that conflicts with the required direct direction
   produces `null_not_rejected`; agreement cannot rescue aggregate failure.

Population parity has no adequacy strata: exact equality is required, and any
failure is `invalid_execution`. No control warning, adequate subgroup,
ascending sensitivity, or Deployment-per-Miner result may rescue a failed
aggregate primary criterion. When all applicable controls pass, disposition
continues through the precedence above.

## 10. Gated Deployment-per-Miner disposition

Record exactly one secondary disposition:

1. `paired_improvement_supported`;
2. `paired_improvement_not_established`; or
3. `paired_comparison_insufficient`.

`paired_improvement_supported` requires an open primary gate, identical paired
population, valid reconstruction, and a two-sided 95% interval whose lower
bound is greater than zero.

`paired_improvement_not_established` applies when the comparison is valid and
adequately supported but the gate is closed or the 95% lower bound is not
greater than zero. When the gate is closed, the estimate and interval are
descriptive only and the record must say so.

`paired_comparison_insufficient` applies when valid paired evidence lacks the
population or uncertainty support required for the fixed comparison. An
invalid execution has no secondary scientific disposition.

The secondary disposition never changes the primary disposition and does not
establish conditional, causal, learned-model, Strategy, or material
incremental value.

## 11. Confirmation boundary

An initial favorable result remains provisional. Final RQ-003
`alternative_supported` authority requires a separately governed confirmation
execution whose population is:

- chronologically later than every initial decision;
- immutable and disjoint from the initial population;
- non-overlapping in rounds, observations, source evidence, and outcome
  evidence;
- the first consecutive eligible population under a prospectively frozen
  collection boundary;
- free of performance-based stopping; and
- sufficient for five inferentially adequate chronological folds.

The confirmation must preserve without weakening:

- signal formula, exact representation, primary direction, decision point,
  tie rules, and procedures;
- metrics, paired populations, exclusions, outcome provenance, missingness,
  uncertainty, baseline family, support thresholds, stability controls, and
  interpretation;
- same-direction fold and adequate-stratum requirements; and
- both adjusted primary lower-bound requirements.

Before any confirmation outcome access, separate prospective governance must
freeze the immutable collection identity and terminal/cap rule. This protocol
does not fabricate a terminal boundary for data that does not yet exist. The
future rule must select the first consecutive eligible population rather than
stop when performance is favorable. Confirmation requires its own immutable
identity, artifacts, finding, and authority chain.

The initial archive alone cannot establish final alternative support,
Strategy admission, or production use. A failed confirmation records the
governed negative or insufficient conclusion; it may not be replaced by a
later favorable interval.

## 12. Invalidity criteria

The experiment is invalid if, among other equivalent authority failures:

- outcome or post-decision information enters measurement, Feature Set,
  ranking, baseline, comparator, tie handling, or pre-outcome exclusions;
- ranking is not frozen before outcome access;
- candidate identity breaks an exact Share-Imbalance tie;
- a zero total is repaired or any forbidden transformation changes a value;
- noncanonical or floating arithmetic changes an identity or ordering;
- procedures use different decisions, candidates, or labeled rounds;
- missing, ambiguous, conflicting, or legacy-unspecified outcomes are
  imputed, fabricated, counted as misses, or silently accepted;
- unsupported revisions are pooled;
- rows, observations, candidates, or rounds cross temporal partitions;
- any frozen scientific choice changes after outcome access;
- the secondary gate, sensitivity, subgroup, or diagnostic rescues a failed
  primary condition;
- population or disposition accounting fails to reconcile;
- canonical authority, identity, artifact, Replay, provenance, dependency,
  or manifest reconstruction fails;
- deterministic regeneration differs where byte identity is required;
- execution is nonconformant with Research Execution Specification v2 or
  `outcome_aware_v1`; or
- Strategy, launch, allocation, control, economic, Paper Miner, Live Miner,
  or real-capital behavior enters the experiment path.

An invalid execution stops without scientific interpretation. Correction
requires prospective versioning as appropriate.

## 13. Required immutable bindings and artifacts

Before implementation or execution authorization, freeze and record:

- this protocol revision and content identity;
- the frozen Minimum-Effect Scope Clarification v1 identity;
- source commit S and experiment configuration identity;
- Research Execution Specification v2 and `outcome_aware_v1` identities;
- dataset persisted-byte and logical identities;
- derived Replay and homogeneous protocol-revision identities;
- both fundamental-measurement authority chains;
- Share-Imbalance and Deployment-per-Miner semantic, definition,
  implementation, dependency, eligibility, and executable-binding identities;
- Feature Set, all procedures, seed domains, binary64 numeric contract,
  metric, fold, support, uncertainty, disposition, confirmation, and artifact
  identities; and
- every artifact declaration below.

An authorized execution must produce every shared artifact required by
Research Execution Specification v2, including immutable bindings, validated
external-source provenance, complete ordered population accounting, frozen
outcome-blind provenance, one canonical outcome-blind ranking primary
artifact, declared outcome-source authority, complete outcome dispositions,
canonical evaluation artifacts, and one sealed outcome-aware Experiment Audit
Manifest.

Experiment-specific artifacts must cover:

1. decision selection, ranked population, and complete dispositions;
2. fundamental-measurement metadata, identities, executable bindings, and
   `MeasurementVector` provenance;
3. exact Share-Imbalance and Deployment-per-Miner definitions, values,
   rational conformance, zero cases, and immutable identities;
4. the one-scalar Feature Set schema and identity;
5. all four required procedure definitions and identities plus the ascending
   sensitivity;
6. candidate values, exact ranks, and tie groups for every ranked decision;
7. frozen outcome-blind rankings and outcome-source/provenance join report;
8. missingness, exclusion, lifecycle, and population reconciliation;
9. the complete decision-neutral labeled-versus-missing chronology,
   observation-count, gap, cadence, decision-distance, lifecycle, collector-
   regime, and collector-session tables;
10. collector-regime keys, metadata reconciliation, exact comparability state,
    warning/insufficiency reasons, and bounded-generalization statement;
11. observation-count, exact-gap, cadence, and decision-distance
    distributions;
12. five-fold chronology and control-family adequacy/conflict reports;
13. lifecycle, provenance, cadence, and collector-regime sensitivity reports;
14. complete primary, incremental, secondary, and diagnostic metrics;
15. exact binary64 paired round-level reciprocal-rank differences;
16. one deterministic bootstrap configuration, replicate schedule, outputs,
    97.5% primary intervals, and 95% gated interval;
17. primary and secondary gate/disposition records;
18. leakage, protocol-control, future-information, and deterministic-
    reconstruction audits; and
19. the confirmation-required continuation record.

Every artifact must satisfy canonical encoding, identity, dependency, digest,
byte-count, record-count, population, and reconstruction contracts. External
sources retain separate persisted-byte and canonical logical identities.

## 14. Execution Readiness compatibility declaration

A future implementation must fit the frozen Execution Readiness architecture
without changing this scientific protocol or weakening its outcome boundary.
Before any official prospective evaluation:

- S must contain the frozen protocol, implementation, declarative experiment
  configuration, selected historical/prospective schema authority, registered
  production adapter authority, and projection contract required to prepare
  this exact experiment;
- prospective Phase-3B evidence preparation must bind the dataset declaration,
  adapter, ordered inputs, source/runtime/dependency authority, profile
  `outcome_aware_v1`, artifact declarations, worker authority, and scientific
  protocol identities without opening outcomes;
- a canonical readiness-record-v2 candidate must bind the reconstructed
  readiness identity and the complete outcome-free readiness authority;
- only a successful `READINESS_VALIDATED` result may precede publication of
  the exact detached evidence graph in a qualifying E;
- R remains a separate path-only readiness seal; and
- current readiness may return `EXECUTION_READY` only after it independently
  reconstructs E, R, the evidence graph, S, and current declared external
  inputs from one coherent freshly fetched H.

E and R attest durability and current authority only. They do not establish a
scientific result, open outcomes, execute the experiment, or authorize launch.
`EXECUTION_READY` permits the later launch-validation lifecycle to begin; it
does not mean launch validation passed or capital may be deployed.

This draft creates no adapter, projection contract, registry member,
candidate, E, R, readiness record, or execution authority. If a future
implementation discovers that scientific material required here cannot be
represented under frozen Execution Readiness authority, it must stop for
separate governance rather than reinterpret this protocol.

## 15. Scientific and governance freeze boundary

Before any Experiment 5 implementation or outcome access, targeted review and
freeze must preserve exactly:

- signal formula, inputs, totals, sign, exact rational form, zero rules,
  direction, and ties;
- Feature Set and all primary, baseline, comparator, and sensitivity
  procedures;
- canonical seed domains and deterministic constructions;
- Minimum-Effect Scope Clarification v1 and the bounded no-positive-`delta_min`
  direct-information interpretation;
- normative binary64 reciprocal-rank, paired-difference, mean, bootstrap, and
  percentile evaluation semantics;
- dataset, source, protocol revision, decision point, population, chronology,
  folds, candidate set, and parity rules;
- outcome provenance, missingness, exclusions, support, and insufficiency;
- primary and incremental estimands, metrics, uncertainty, familywise control,
  fixed-sequence gate, and intervals;
- no-numeric-materiality rule and interpretation limits;
- primary and secondary dispositions and non-rescue rules;
- confirmation properties and the requirement for a later prospectively
  frozen collection boundary; and
- required authority bindings, artifacts, and Execution Readiness interface.

Implementation may choose ordinary internal code organization only when it
cannot change canonical bytes, identities, eligible population, ranks,
metrics, inference, disposition, information flow, or authority. Any such
choice that could change scientific meaning requires prospective protocol
revision before outcome access.

## 16. Completion and stopping boundary

The bounded initial experiment is complete only when a conformant execution
preserves every required artifact, records exactly one primary disposition and
one applicable secondary disposition, and records confirmation as still
required for any favorable initial result.

Completion does not authorize:

- final RQ-003 `alternative_supported` from the initial archive;
- scientific, causal, material, economic, or Strategy superiority to
  Deployment per Miner;
- a reusable or combined Feature Set;
- procedure or threshold tuning;
- Strategy admission, Decision Engine use, portfolio simulation, Paper Miner,
  Live Miner, launch, allocation, control, recovery, or real-SOL activity; or
- a confirmation execution without its own prospective collection governance
  and authority chain.

A favorable initial result authorizes only external review of whether to
prepare the required disjoint confirmation protocol. A negative, insufficient,
or invalid result does not authorize a rescue experiment or post-outcome
protocol change.
