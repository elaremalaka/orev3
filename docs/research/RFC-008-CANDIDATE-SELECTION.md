# RFC-008 Candidate Selection Memorandum

Status: **Approved and frozen; not validation evidence**

## Decision

The proposed RFC-008 candidate is `highest_reward_top4_v1` version `1.0.0`.
This selection authorizes neither implementation nor collection.

The choice was made under the rule below before the eligible evidence was
applied:

1. collapse implementation aliases;
2. exclude controls, the retired RFC-007 arm, unavailable live model
   inference, and any strategy requiring holdout tuning;
3. require a deterministic definition using inputs available at the decision
   snapshot, documented configuration, and at least 300 independent
   pre-boundary rounds;
4. rank the remaining candidates by reconstructed after-fee ROI in the locked
   RFC-008 scenario;
5. use round-level hit rate, chronological stability, coverage, and
   reproducibility as secondary checks; and
6. select exactly one eligible candidate for a prospective test, without
   interpreting selection as evidence that it will succeed.

No pass threshold was imposed on historical ROI because the requested task is
to select one candidate for prospective testing. Negative or unstable
historical evidence is retained prominently and the future success thresholds
are not weakened.

## Immutable training boundary

Candidate selection uses only rounds `342132` through `342570`, inclusive.
The latest eligible observation is
`2026-07-23T15:48:13.823493Z`. There are 439 independent rounds.
The latest finalized-outcome evidence retrieval is
`2026-07-24T01:19:48.011670Z`. Evidence was frozen from the clean worktree at
starting commit `1181c32c9296c572697f5bb0c285d2566a2378e7`.

Eligible artifacts are identified by content hash in
`docs/research/rfc008/preholdout_evidence_v1.json`. The principal inputs are:

- canonical observations, SHA-256
  `4050084e141c1e6c5f1f415b39c4c2ee39f1037eee57379dabf44945c943c92c`;
- lifecycle outcomes, SHA-256
  `435a73c91b5c525ffc3a339dcb128d2a288b93eb47f1a253bf919d2853f25b02`;
- RFC-005 results, SHA-256
  `1191b090ce47904628c3036b24b2936af23a0dcafd84a8ba98a2f4139c7ca780`;
  and
- RFC-005 strategy definitions, SHA-256
  `c76de846dcc786c9b57aec6fa25a019ba5df3fd9ce0ccbf4f960d5ae7f4e988c`.

RFC-007 rounds and results were not used to score or tune the candidate.
RFC-007 is used only to establish that the least-crowded arm is retired and to
define it as a historical comparator. No RFC-008 observation exists in the
eligible round range. Every future RFC-008 observation, decision, outcome, and
aggregate is prohibited from candidate selection or tuning.

## Candidate universe

| Strategy | Disposition | Reason |
|---|---|---|
| `highest_reward_top4_v1` | Eligible; selected | Fully specified from `reward_raw`; deterministic; 439 independent rounds; best reconstructed after-fee ROI among eligible candidates in the locked scenario. |
| `least_deployed_top4_v1` | Eligible; not selected | Fully specified and reproducible, but lower round hit rate and lower reconstructed after-fee ROI. |
| `least_crowded_v1` | Comparator only | Exact miner-count ordering used by RFC-007; retired from candidacy after RFC-007. |
| `existing_least_crowded`, `least_miner_count`, `lowest_miner_share` | One alias group | All sort ascending miner count and then square index; not independent candidates. |
| `random_top4_v1` | Primary baseline only | A control distribution, not a candidate selected for advancement. |
| `no_deploy_v1` | Economic reference only | Defines zero deployment and zero paper return; it is not a predictive strategy. |
| RFC-004 logistic, random-forest, and histogram-gradient-boosting arms | Excluded | Historical OOS rankings exist, but there is no serialized live inference pipeline or complete live-compatible ranking vector. |
| RFC-005 rank ensembles | Excluded | The tracked strategy artifact marks them unavailable because complete component rank vectors are absent. |
| Any tuned timing, sizing, threshold, ensemble, or transformed-reward variant | Excluded | It is not frozen from pre-RFC-008 information and would create discretionary holdout tuning risk. |

## Evidence at the common decision snapshot

For each round, the screen chose the first complete 25-square observation with
`slots_remaining <= 75`, equivalent to at most 30.0 seconds under the
repository's fixed 0.4-second conversion. All 439 rounds supplied a complete
snapshot. Selected snapshots ranged from 15.2 to 30.0 seconds remaining.

The historical accounting scenario exactly matches the proposed experiment:
four squares, 50,000 lamports total, equal 12,500-lamport allocation, 5,000
lamports deploy fee, and a 5,000-lamport claim fee after positive return.
Accounting is reconstructed price-taking evidence, not wallet-realized
economics.

| Strategy | Independent rounds | Hits | Hit rate | Reconstructed after-fee ROI | 95% round-bootstrap ROI interval |
|---|---:|---:|---:|---:|---:|
| `highest_reward_top4_v1` | 439 | 75 | 17.08% | -19.64% | -37.78% to -0.58% |
| `least_deployed_top4_v1` | 439 | 60 | 13.67% | -36.96% | -53.91% to -19.63% |
| `least_crowded_top4_v1` | 439 | 63 | 14.35% | -34.00% | -50.89% to -16.02% |
| `random_top4_v1` | 439 | 72 | 16.40% | -24.02% | -41.78% to -5.57% |

RFC-005 provides a separate sensitivity check: at its reference scenario of
one selected square and 1,000,000 lamports across 176 OOS rounds,
`highest_reward` was the validation-selected best fixed heuristic and reported
+6.58% after-fee ROI. That opportunity-level configuration is not treated as
confirmation of the top-four candidate. The sign reversal in the locked
RFC-008 scenario is an important instability warning.

## Selection rationale

`highest_reward_top4_v1` ranks first among the two eligible candidates on the
predefined primary criterion and also has the higher round hit rate. Its
definition requires only the contemporaneous 25-value `reward_raw` vector and
an ascending-square tie break. It needs no fitted parameters, model artifact,
future state, or finalized outcome.

The evidence does **not** establish effectiveness. Its reconstructed
after-fee ROI is negative, its lower and upper chronological behavior is
unstable, and its paired advantage over random is only 0.68 percentage points.
The purpose of RFC-008 is therefore a stringent prospective falsification
test, not a progression toward live deployment.

## Paired disagreement and power

Against the frozen deterministic random top-four baseline:

- candidate-only hits: 58;
- random-only hits: 55;
- both hit: 17;
- neither hit: 309;
- discordant rounds: 113 of 439, or 25.74%;
- historical paired difference: +0.68 percentage points;
- paired round-bootstrap 95% interval: -4.10 to +5.47 points; and
- historical exact one-sided McNemar p-value: 0.4254.

Using the 25.74% planning discordance rate, a +6-point alternative, and exact
one-sided McNemar alpha 0.025, 400 rounds provide 62.56% test power. The first
integer sample size reaching 80% is 586. The proposal therefore freezes 600
analyzable rounds, which provide 80.96% test power.

The separate requirement that the observed effect be at least +6 points makes
the joint probability of success approximately one half when the true effect
is exactly at that boundary. That is intentional: +6 points is a minimum
relevant observed effect, not merely the alternative used for test-power
planning.

The started-round cap is 632, equal to `ceil(600 / 0.95)`, and the calendar
cap remains 14 days. Reaching either cap without 600 analyzable rounds is
inconclusive unless an explicit failure condition has already occurred.

## Overfitting and sensitivity concerns

- Candidate selection examined a small deterministic universe, but it still
  creates selection bias; RFC-008 must be treated as the first confirmatory
  test.
- All 439 rounds occurred in a short historical interval and may not represent
  later board regimes.
- Only one of four chronological blocks produced positive candidate ROI.
- Historical final outcomes comprise 58 contemporaneously observed and 381
  enriched outcomes; they were labels only, never candidate inputs.
- Reward ties are resolved by square index. This deterministic rule may behave
  like a low-index prior when all rewards are equal.
- Price-taking economics ignore the strategy's deployment impact.
- The RFC-005 positive reference-scenario result does not transport cleanly to
  the frozen top-four, 50,000-lamport design.

These concerns argue for retaining, not weakening, the preregistered success
gates.
