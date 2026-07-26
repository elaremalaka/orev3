# RFC-008 — Preregistered Round-Level Strategy Evaluation

Status: **Draft for human approval; collection not authorized**

## 1. Purpose

RFC-008 defines a prospective, round-level paper experiment for one frozen
candidate strategy and locked comparators. It corrects the principal
inferential limitation of RFC-007: many observation rows but few independent
finalized rounds.

This RFC is a design and preregistration artifact. It does not authorize:

- starting an RFC-008 collection;
- changing the running observer or RFC-007 collector;
- strategy tuning on the RFC-008 holdout;
- wallet access, transaction construction, signing, submission, or claiming;
- live or controlled-live deployment; or
- using paper economics as wallet-realized economics.

Implementation and collection require separate approvals after the unresolved
choices in Section 18 are frozen.

## 2. Primary experimental unit

The primary unit is one eligible, durably finalized ORE round.

Each eligible round contributes exactly one decision snapshot per strategy.
All strategies receive the same pre-outcome board snapshot. Repeated observer
snapshots may be retained for engineering diagnostics but are not additional
experimental units.

The canonical decision snapshot is the first complete 25-square observation
at or below 30.0 seconds remaining. If no such snapshot exists before
finalization, the round is ineligible and is recorded with an exclusion
reason. No later snapshot may be substituted after the outcome is known.

## 3. Locked strategy arms

All arms use four unique squares. Except for no-deploy, paper sizing is 50,000
lamports with equal allocation.

| Arm | Definition | Role |
|---|---|---|
| `random_top4_v1` | Four squares selected by a deterministic SHA-256 seed derived from the preregistration hash and round ID | Primary baseline |
| `least_crowded_v1` | Ascending miner count, then ascending square index | Deterministic baseline |
| `rfc007_frozen_reference_v1` | Exact RFC-007 `existing_least_crowded` v1.0.0 configuration | Historical reference |
| `candidate_v1` | One serialized strategy selected and frozen using only pre-holdout data | Candidate |
| `no_deploy_v1` | No squares, zero intended deployment, zero paper fees | Economic control |

The current implementation maps `existing_least_crowded`,
`least_miner_count`, and `lowest_miner_share` to the same miner-count ordering.
Therefore `least_crowded_v1` and `rfc007_frozen_reference_v1` are expected to
produce identical decisions. They remain separately labeled for provenance,
but they are one effective statistical arm and must not be counted as
independent confirmations.

## 4. Candidate selection and leakage boundary

The candidate may be selected only from data whose finalized rounds precede
the RFC-008 holdout marker.

Before the marker is frozen, the following must be committed:

1. candidate implementation and version;
2. serialized artifact, if applicable;
3. exact feature and input schema;
4. candidate-training round IDs and hashes;
5. candidate-selection procedure and candidate universe;
6. deterministic inference test vectors;
7. all strategy and accounting configuration hashes;
8. this RFC and its final approval amendment; and
9. the paired power calculation.

RFC-007 outcomes may be used as historical training or design data only if
declared before candidate selection. If they are used, RFC-007 cannot be
reported as candidate validation.

No RFC-008 holdout observation, decision, outcome, or interim aggregate may
alter the candidate, baselines, sizing, timing rule, exclusions, hypotheses,
or stopping rule.

## 5. Holdout boundary and sample

The holdout begins at the first eligible round whose round ID is strictly
greater than the round ID recorded in an immutable RFC-008 start marker.

The marker must include:

- protocol and schema versions;
- repository commit and branch;
- candidate artifact and configuration hashes;
- baseline definitions and random seed;
- decision-snapshot rule;
- source identities and cursors;
- latest pre-holdout round ID;
- outcome-acquisition configuration;
- accounting assumptions;
- primary and secondary hypotheses;
- sample size and stopping rule; and
- a deterministic preregistration hash.

The minimum analyzable holdout is **400 consecutive eligible, resolved,
independent rounds**.

Collection stops for analysis at the first of:

1. 400 analyzable rounds;
2. 450 started rounds;
3. 14 elapsed calendar days; or
4. a safety, provenance, marker, source-integrity, or configuration failure.

There is no performance-based early stopping and no interim efficacy analysis.
If fewer than 400 analyzable rounds are available at a terminal boundary, the
result is inconclusive or operationally failed as specified in Section 14.

## 6. Power and precision

The planning benchmark is a 16% hit probability for four uniformly random
squares.

Using a conservative one-sample normal approximation, one-sided alpha 0.025:

- about 317 independent rounds are required for 80% power to distinguish 22%
  from 16%;
- 400 rounds provide approximately 88% power under that assumption; and
- at 16%, 400 rounds provide an approximate 95% half-width of 3.6 percentage
  points.

These calculations treat rounds as independent and do not treat within-round
snapshots as new observations. They are planning approximations, not evidence
from the RFC-008 holdout.

Because the primary comparison is paired and the discordance rate is not yet
frozen, the final preregistration amendment must calculate McNemar power using
only pre-holdout/training rounds. If that calculation requires more than 400
rounds, the larger number must be approved and frozen before the marker.
Sample size may not be reduced after holdout collection begins.

## 7. Primary hypothesis and metric

Primary metric:

`paired round-level top-four hit-rate difference =
candidate_v1 hit - random_top4_v1 hit`

Primary hypothesis:

- H0: the candidate has no positive paired hit-rate advantage over the locked
  random top-four baseline.
- H1: the candidate has a positive paired hit-rate advantage.

The primary test is an exact one-sided McNemar test at alpha 0.025. The
confidence interval is a two-sided 95% paired round bootstrap interval. The
point estimate must also exceed the minimum relevant improvement of six
percentage points.

The 0.025 alpha leaves error budget for one confirmatory economic gate. All
other comparisons are secondary or descriptive.

## 8. Secondary metrics

Secondary metrics are:

1. candidate hit rate and Wilson interval by round;
2. paired hit-rate difference versus `least_crowded_v1`;
3. gross SOL return under the locked price-taking calculation;
4. net SOL before fees;
5. net SOL after configured paper fees;
6. net SOL after directly observed fees, when separately authorized and
   available;
7. ROI before and after fees;
8. profitable-round rate;
9. maximum drawdown and longest losing streak in round order;
10. Motherlode ORE raw return;
11. base ORE raw return when directly obtainable;
12. total ORE raw return when all components are directly supported;
13. outcome, transaction, fee, return, and claim completeness;
14. decision and finalization latency;
15. results by fixed chronological block; and
16. results by outcome and accounting provenance.

No secondary metric may replace a failed primary metric.

## 9. Economic accounting

Paper price-taking accounting remains:

`allocation on winning square × total winnings ÷
final winning-square deployment`

The locked paper assumptions are:

- intended deployment: 50,000 lamports;
- allocation: equal over four squares;
- deploy fee: 5,000 lamports;
- claim fee: 5,000 lamports only after positive reconstructed SOL or
  Motherlode return;
- priority fee: zero unless changed in the final pre-marker amendment;
- failed-transaction cost: zero in paper mode;
- no-deploy control: zero deployment, return, and fees; and
- deployment is treated as cost while total winnings is the gross pool.

Price-taking calculations do not model deployment impact and are classified
`reconstructed_paper_not_wallet_realized`.

Direct participant economics, if later authorized, must be stored separately:

- actual deployment debit;
- base fee, priority fee, and other transaction costs;
- failed-transaction cost;
- claim timing and claim fee;
- gross and net wallet SOL change;
- ORE token balance change;
- base ORE;
- Motherlode ORE; and
- claim and transaction identifiers.

Configured fees may not be substituted for missing realized fees. A realized
economic result requires at least 95% complete transaction, fee, wallet,
reward, and claim reconciliation and a separately approved live-safety RFC.

## 10. Motherlode and ORE treatment

Motherlode is reported separately from base ORE.

- Motherlode return is calculated only from a directly observed finalized
  round value and the locked allocation rule.
- Base ORE remains `unavailable` unless a direct authoritative source and unit
  conversion are validated before the marker.
- Missing base ORE is never treated as zero.
- Total ORE is unavailable unless every included component is available.
- SOL and ORE are not combined into one value without a preregistered price
  source and timestamp rule.

## 11. Durable finalized outcomes

The existing observer polls the current round and emits a transition only after
it observes the next round. The existing collector accepts explicit finalized
snapshots but correctly refuses to infer the prior winner from a transition.
RFC-007 demonstrated that this leaves a gap in which the prior round account
can disappear before it is durably captured.

RFC-008 must use a separate durable outcome-acquisition component rather than
modifying the currently running observer.

At each transition it must:

1. durably enqueue the prior round before attempting resolution;
2. derive and store the exact round PDA;
3. poll authoritative finalized state;
4. retry unresolved rounds across restarts;
5. preserve every provider response hash and commitment;
6. accept an outcome only after full account validation;
7. maintain explicit pending, finalized, conflicted, quarantined, and failed
   states; and
8. prove that every started eligible round reaches a terminal state.

No round transition may silently remove a pending round.

## 12. Missing, conflict, and quarantine policy

- A round without a directly observed durable final outcome remains pending.
- Retry uses bounded exponential backoff with jitter derived from the round ID,
  capped at five minutes.
- A round still unresolved 24 hours after transition is quarantined.
- Post-hoc dual-provider recovery may be retained as sensitivity evidence but
  is not part of the primary directly observed outcome analysis.
- Provider, owner, round ID, winner, or canonical field disagreement places the
  round in `conflicted` and pauses analysis readiness.
- Malformed or non-finite evidence is rejected.
- A quarantined or conflicted round does not count toward the 400 analyzable
  rounds and is never silently dropped; the next eligible round may replace it
  under the fixed stopping rule.
- More than 5% quarantined, missing, conflicted, or otherwise unanalyzable
  started rounds is an operational failure.
- Any marker, strategy, configuration, cursor, source-integrity, or provenance
  failure stops collection and requires human review.

## 13. Analysis plan

Analysis uses one row per eligible finalized round and preserves round order.

Primary:

- exact one-sided McNemar test versus `random_top4_v1`;
- paired hit-rate difference;
- two-sided 95% paired round bootstrap interval; and
- the six-percentage-point minimum relevant improvement.

Economic confirmatory gate:

- candidate mean net SOL after fees versus the zero-return no-deploy control;
- one-sided paired randomization test at alpha 0.025; and
- two-sided 95% round bootstrap interval for candidate ROI after fees.

Secondary comparisons use Holm correction within metric families. Results for
the historical RFC-007 alias are descriptive because it duplicates the
least-crowded ordering.

All exclusions, missingness, conflicts, provenance classes, and replacements
are reported in a round-flow table. No row-level test may claim a sample size
larger than the number of independent rounds.

## 14. Advancement decision table

| Disposition | Exact criteria |
|---|---|
| **Success** | At least 400 analyzable rounds; primary McNemar one-sided `p < 0.025`; paired hit-rate difference point estimate at least `+0.06`; lower 95% paired bootstrap bound greater than `0`; candidate reconstructed ROI after fees greater than `0`; lower 95% round-bootstrap ROI bound greater than `0`; no safety failure; no configuration drift; and missing/conflicted/quarantined rate at most 5%. |
| **Failure** | Upper 95% paired hit-rate-difference bound is at most `0`, or upper 95% ROI-after-fees bound is at most `0`, or any live-action/safety boundary is violated, or missing/conflicted/quarantined rate exceeds 5%. |
| **Inconclusive** | Terminal stopping boundary is reached without meeting all success criteria and without meeting a failure criterion; fewer than 400 analyzable rounds; a positive but smaller-than-six-point hit advantage; or incomplete realized accounting. |
| **Eligible for controlled-live design review** | Paper **Success**, plus separately collected realized accounting completeness of at least 95%, directly observed fees and wallet returns, positive realized ROI with lower 95% bound greater than `0`, and approval of a separate capital-limit, kill-switch, and transaction-safety RFC. |

Success does not itself authorize live deployment.

## 15. Prohibited changes after marker freeze

After the marker is frozen, no one may change:

- candidate code, model, artifact, features, or parameters;
- comparator definitions or random seed;
- square count, sizing, allocation, or timing rule;
- fee or reward accounting;
- hypotheses, alpha, confidence level, or effect threshold;
- eligibility, missingness, recovery, quarantine, or stopping rules;
- holdout boundary or target round count; or
- primary/secondary metric designation.

A required correctness fix invalidates the current marker and requires a new
versioned preregistration and fresh holdout.

## 16. Required schema and provenance

The implementation should add versioned, append-only records for:

- experiment identity and immutable marker;
- round eligibility and exclusion;
- one canonical decision snapshot per round;
- decisions for every locked strategy arm;
- pending outcome acquisition and retry attempts;
- finalized outcomes and conflicts;
- paper economic accounting by arm;
- optional participant transaction and fee evidence;
- wallet SOL and ORE balance observations;
- claims and claim timing;
- round-level reconciliation; and
- analysis inclusion and exclusion.

Every evidence record must include source type, source reference, content hash,
capture time, protocol time, commitment/finality, schema version, producer
version, configuration hash, and conflict status.

## 17. Safety and process isolation

The currently running observer and RFC-007 collector are out of scope for
modification. RFC-008 implementation must use new versioned paths, process
labels, writer leases, and markers.

No private key, signer, transaction builder, submission, or claim path belongs
in the paper collector or outcome resolver. Optional realized participant
accounting requires a separately authorized adapter and may not be enabled by
this RFC alone.

## 18. Human approvals required before implementation or collection

1. Candidate strategy universe and deterministic selection rule.
2. Candidate artifact and training-round boundary.
3. The 30-second decision snapshot threshold.
4. Whether 400 rounds remains sufficient after paired McNemar power is
   calculated from pre-holdout data.
5. Maximum 450 started rounds and 14-day calendar cap.
6. The six-percentage-point minimum relevant hit improvement.
7. Alpha allocation of 0.025 predictive and 0.025 economic.
8. Whether recovered outcomes are excluded from primary analysis as specified.
9. Fee assumptions for paper analysis.
10. Whether any realized participant accounting phase will be proposed under a
    separate live-safety RFC.

Until these choices are approved and committed, no RFC-008 marker or
collection may be created.
