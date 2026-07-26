# RFC-008 — Preregistered Round-Level Strategy Evaluation

Status: **Approved and frozen for paper-only implementation; marker creation
and collection not authorized**

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

Paper-only implementation is approved. Marker creation and collection require
separate explicit authorization after implementation verification.

## 2. Primary experimental unit

The primary unit is one eligible, durably finalized ORE round.

Each eligible round contributes exactly one decision snapshot per strategy.
All strategies receive the same pre-outcome board snapshot. Repeated observer
snapshots may be retained for engineering diagnostics but are not additional
experimental units.

The canonical decision snapshot is the first complete 25-square observation
at or below 30.0 seconds remaining. This is exactly
`slots_remaining <= 75` under the repository's fixed 0.4-second slot
conversion. If no such snapshot exists before finalization, the round is
ineligible and is recorded with an exclusion reason. No later snapshot may be
substituted after the outcome is known.

The pre-holdout audit found a complete qualifying snapshot in all 439 eligible
historical rounds. The selected snapshots contained exactly 25 unique squares
and ranged from 15.2 to 30.0 seconds remaining. `miner_count`,
`deployed_lamports`, and `reward_raw` were available to every comparison arm.
Thirty seconds is therefore retained as the latest common reliable trigger.

## 3. Locked strategy arms

All arms use four unique squares. Except for no-deploy, paper sizing is 50,000
lamports with equal allocation.

| Arm | Definition | Role |
|---|---|---|
| `random_top4_v1` | Rank each square by SHA-256 of `rfc008-random-top4-v1-seed-20260725:round_id:square_index`, bytewise ascending, then square index | Primary baseline |
| `least_crowded_v1` | Ascending miner count, then ascending square index | Deterministic baseline |
| `rfc007_frozen_reference_v1` | Exact RFC-007 `existing_least_crowded` v1.0.0 configuration | Historical reference |
| `highest_reward_top4_v1` | Descending `reward_raw`, then ascending square index | Candidate |
| `no_deploy_v1` | No squares, zero intended deployment, zero paper fees | Economic control |

The current implementation maps `existing_least_crowded`,
`least_miner_count`, and `lowest_miner_share` to the same miner-count ordering.
Therefore `least_crowded_v1` and `rfc007_frozen_reference_v1` are expected to
produce identical decisions. They remain separately labeled for provenance,
but they are one effective statistical arm and must not be counted as
independent confirmations.

## 4. Candidate selection and leakage boundary

The immutable candidate-selection boundary is:

- rounds `342132` through `342570`, inclusive;
- latest eligible observation
  `2026-07-23T15:48:13.823493Z`;
- latest finalized-outcome evidence retrieval
  `2026-07-24T01:19:48.011670Z`;
- 439 independent rounds; and
- repository starting commit
  `1181c32c9296c572697f5bb0c285d2566a2378e7`; and
- content hashes listed in
  `docs/research/rfc008/preholdout_evidence_v1.json`.

RFC-007 data were not used to score or tune the replacement candidate.
RFC-007 establishes only that its least-crowded arm is a retired historical
comparator. All RFC-008 holdout observations are strictly prohibited from
selection or tuning.

The predefined selection rule collapses aliases; excludes controls, the
retired arm, unavailable live model inference, and strategies requiring
holdout tuning; requires deterministic live-available inputs, documented
configuration, and at least 300 independent pre-boundary rounds; then ranks
eligible candidates by reconstructed after-fee ROI, with round hit rate,
stability, coverage, and reproducibility as secondary checks.

The distinct eligible candidates were `highest_reward_top4_v1` and
`least_deployed_top4_v1`. `highest_reward_top4_v1` was selected. Its complete
specification is
`docs/research/rfc008/rfc008_candidate_v1.json`, with configuration SHA-256
`e60722e845d6364c41d28ebc7d1641f8c8726766f87bdb838f3822decf50a372`.

This selection does not constitute positive performance evidence. In the
locked historical scenario its after-fee ROI was -19.64%, and its paired hit
advantage over random was only +0.68 percentage points.

Before the marker is frozen, the implementation, deterministic test vectors,
configuration hashes, this approved RFC, and the paired power calculation
must be committed. No RFC-008 holdout observation, decision, outcome, or
interim aggregate may alter any frozen choice.

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

The minimum analyzable holdout is **600 consecutive eligible, resolved,
independent rounds**.

Collection stops for analysis at the first of:

1. 600 analyzable rounds;
2. 632 started rounds;
3. 14 elapsed calendar days; or
4. a safety, provenance, marker, source-integrity, or configuration failure.

There is no performance-based early stopping and no interim efficacy analysis.
If fewer than 600 analyzable rounds are available at a terminal boundary, the
result is inconclusive or operationally failed as specified in Section 14.

## 6. Power and precision

The pre-holdout paired table for `highest_reward_top4_v1` versus
`random_top4_v1` contains:

- 58 candidate-only hits;
- 55 random-only hits;
- 17 joint hits;
- 309 joint misses; and
- 113 discordant rounds out of 439, or 25.74%.

At that frozen discordance rate, exact one-sided McNemar alpha 0.025 and a
+6-percentage-point alternative, 400 rounds provide 62.56% test power. The
first integer sample size reaching 80% is 586 rounds. The final minimum is
therefore 600 analyzable rounds, providing 80.96% test power.

The separate observed-effect gate of at least +6 points remains in force.
When the true effect is exactly at the gate, the probability that a noisy
point estimate also clears the gate is approximately one half; this is
intentional and is not a reason to weaken the minimum relevant effect.

The 632-started-round cap is `ceil(600 / 0.95)`. Sample size may not be
reduced after holdout collection begins. Repeated snapshots are not
independent units.

## 7. Primary hypothesis and metric

Primary metric:

`paired round-level top-four hit-rate difference =
highest_reward_top4_v1 hit - random_top4_v1 hit`

Primary hypothesis:

- H0: the candidate has no positive paired hit-rate advantage over the locked
  random top-four baseline.
- H1: the candidate has a positive paired hit-rate advantage.

The primary test is an exact one-sided McNemar test at alpha 0.025. The
confidence interval is a two-sided 95% paired round bootstrap interval. The
point estimate must also exceed the minimum relevant improvement of six
percentage points.

The final economic-threshold amendment calculated a conservative pre-holdout
SOL break-even improvement of +4.96 percentage points, rounded upward to +5.
The +6-point predictive gate is therefore retained unchanged. Hit rate alone
is insufficient: the reward-weighted economic gates in Section 13 remain
mandatory.

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
- priority fee: zero;
- failed-transaction cost: zero in paper mode;
- no-deploy control: zero deployment, return, and fees; and
- deployment is treated as cost while total winnings is the gross pool.

`no_deploy_v1` is the confirmatory economic reference and paired economic
comparison arm. It is not a predictive comparator and contributes no hit-rate
observation. Its zero return is a protocol definition, not an estimate of
wallet economics.

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

- A round is **primary-analyzable** only when it has the timely canonical
  snapshot, deterministic decisions for every required arm, a directly and
  durably observed finalized outcome, validated round/PDA/owner/finality
  provenance, and complete fields for the locked primary and economic tests.
- A round without a directly observed durable final outcome remains pending.
- Retry uses bounded exponential backoff with jitter derived from the round ID,
  capped at five minutes.
- A round still unresolved 24 hours after transition is quarantined.
- A quarantined round is **recoverable** only when the frozen recovery protocol
  can obtain deterministic, agreeing, authoritative finalized evidence with a
  complete provenance record. Post-hoc recovery may be retained as sensitivity
  evidence but is never primary-analyzable.
- Provider, owner, round ID, winner, or canonical field disagreement places the
  round in `conflicted` and pauses analysis readiness.
- A round is **excluded** only for a reason determinable without its outcome,
  such as no timely complete snapshot or invalid contemporaneous decision
  inputs. Exclusion reasons are append-only and exclusions never count as
  analyzable replacements after the outcome is known.
- Malformed or non-finite evidence is rejected.
- A quarantined or conflicted round does not count toward the 600 analyzable
  rounds and is never silently dropped; the next eligible round may replace it
  under the fixed stopping rule.
- More than 5% quarantined, missing, conflicted, or otherwise unanalyzable
  started rounds is an operational failure. The denominator is every started
  post-marker round.
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
| **Success** | At least 600 analyzable rounds; primary McNemar one-sided `p < 0.025`; paired hit-rate difference point estimate at least `+0.06`; lower 95% paired bootstrap bound greater than `0`; candidate reconstructed ROI after fees greater than `0`; lower 95% round-bootstrap ROI bound greater than `0`; one-sided paired economic randomization `p < 0.025` versus no-deploy; no safety failure; no configuration drift; and missing/conflicted/quarantined rate at most 5%. |
| **Failure** | Upper 95% paired hit-rate-difference bound is at most `0`, or upper 95% ROI-after-fees bound is at most `0`, or any live-action/safety boundary is violated, or missing/conflicted/quarantined rate exceeds 5%. |
| **Inconclusive** | Terminal stopping boundary is reached without meeting all success criteria and without meeting a failure criterion; fewer than 600 analyzable rounds; a positive but smaller-than-six-point hit advantage; predictive and economic gates disagree; or locked evidence is unavailable. |
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

## 18. Human approval disposition

The ten final proposed decisions, rationale, consequences, and blank
approve/reject fields are in
`docs/research/RFC-008-HUMAN-APPROVAL-CHECKLIST.md`. They cover:

1. candidate and selection rule;
2. candidate artifact and immutable training boundary;
3. the 30-second decision trigger;
4. 600 minimum analyzable rounds;
5. 632 started rounds and 14-day cap;
6. predictive alpha, confidence, and +6-point effect gates;
7. the economic gate;
8. primary outcome provenance and 5% missingness limit;
9. paper fee and accounting assumptions; and
10. the separate authorization boundary for realized accounting and live
    action.

All ten items were approved on `2026-07-25`, subject to the economic-threshold
validation. That validation passed and is frozen in
`docs/research/RFC-008-ECONOMIC-THRESHOLD-APPROVAL-AMENDMENT.md`.

Paper-only implementation is authorized. No RFC-008 marker or collection may
be created until implementation is complete, verified, committed, and
separately authorized.
