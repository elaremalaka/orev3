# RFC-008 Human Approval Checklist

Status: **Approval requested; all fields intentionally unresolved**

Mark exactly one field for each item. Approval of this package does not
authorize implementation or collection.

## 1. Candidate and selection rule

- Proposed value: `highest_reward_top4_v1` version `1.0.0`, selected under the
  frozen rule in `RFC-008-CANDIDATE-SELECTION.md`.
- Rationale: it is the reproducible eligible heuristic with the best
  reconstructed after-fee ROI and highest hit rate in 439 independent
  pre-boundary rounds.
- Consequences: it enters a prospective falsification test despite negative
  historical ROI; no retuning is permitted.
- Approve: `[ ]`
- Reject: `[ ]`

## 2. Candidate artifact and training boundary

- Proposed value: configuration hash
  `e60722e845d6364c41d28ebc7d1641f8c8726766f87bdb838f3822decf50a372`;
  eligible rounds `342132`–`342570`; latest observation
  `2026-07-23T15:48:13.823493Z`.
- Rationale: exact hashes and round/time boundaries make the selection
  reproducible and exclude RFC-007 scoring and all future RFC-008 data.
- Consequences: any later training or candidate change requires a new
  preregistration and fresh holdout.
- Approve: `[ ]`
- Reject: `[ ]`

## 3. Decision trigger

- Proposed value: first complete 25-square snapshot at or below 30.0 seconds
  remaining (`slots_remaining <= 75` at 0.4 seconds per slot).
- Rationale: all 439 pre-boundary rounds have a complete common snapshot;
  all arms use only fields present at that point.
- Consequences: rounds without a qualifying snapshot are explicitly
  ineligible; no post-outcome substitution is allowed.
- Approve: `[ ]`
- Reject: `[ ]`

## 4. Minimum analyzable rounds

- Proposed value: 600 independent, eligible, directly resolved rounds.
- Rationale: exact paired McNemar planning estimates 586 for 80% power at
  alpha 0.025 and a +6-point alternative; 600 provides 80.96%.
- Consequences: the experiment is longer than the draft 400-round plan and
  repeated observations cannot increase the count.
- Approve: `[ ]`
- Reject: `[ ]`

## 5. Stopping caps

- Proposed value: 632 started rounds or 14 calendar days, whichever comes
  first, with no performance-based early stopping.
- Rationale: 632 is `ceil(600 / 0.95)` and aligns with the 5% missingness
  boundary.
- Consequences: reaching a cap below 600 analyzable rounds is inconclusive
  unless a failure condition already applies.
- Approve: `[ ]`
- Reject: `[ ]`

## 6. Predictive thresholds

- Proposed value: exact one-sided McNemar `p < 0.025`, observed paired
  hit-rate improvement at least +0.06, and lower two-sided 95% paired
  round-bootstrap bound greater than zero.
- Rationale: preserves the draft error budget and a practically relevant
  effect without adapting to weak historical results.
- Consequences: a statistically positive but smaller effect is inconclusive,
  not success.
- Approve: `[ ]`
- Reject: `[ ]`

## 7. Economic threshold

- Proposed value: reconstructed after-fee ROI greater than zero, lower
  two-sided 95% round-bootstrap bound greater than zero, and one-sided paired
  randomization `p < 0.025` versus no-deploy.
- Rationale: prediction alone cannot justify advancement when configured paper
  economics are negative.
- Consequences: economic failure or uncertainty prevents success even when the
  predictive gate passes.
- Approve: `[ ]`
- Reject: `[ ]`

## 8. Outcome provenance and missingness

- Proposed value: directly and durably observed finalized outcomes only in
  primary analysis; recovered outcomes only in a separately labeled
  sensitivity analysis; missing/conflicted/quarantined started rounds at most
  5%.
- Rationale: separates prospective capture from post-hoc recovery and makes
  missingness visible.
- Consequences: recovered rounds cannot fill the primary 600-round target.
- Approve: `[ ]`
- Reject: `[ ]`

## 9. Paper fees and economic accounting

- Proposed value: 50,000 lamports deployed; 5,000 deploy fee; 5,000 claim fee
  only after positive reconstructed SOL or Motherlode return; zero priority
  and failed-transaction fees; deployment is cost; total winnings is gross
  pool; base ORE unavailable.
- Rationale: matches the tracked paper assumptions while labeling them as
  configured rather than observed.
- Consequences: report both pre-fee and after-fee ROI; do not call results
  wallet-realized or combine SOL and ORE.
- Approve: `[ ]`
- Reject: `[ ]`

## 10. Realized accounting and live boundary

- Proposed value: no wallet, transaction, signing, submission, claim, or live
  realized-accounting activity under RFC-008; any such phase requires a
  separate safety RFC and authorization.
- Rationale: RFC-008 is a paper experiment.
- Consequences: success does not authorize controlled-live or production
  deployment.
- Approve: `[ ]`
- Reject: `[ ]`

## Overall disposition

- Approve the complete design package for a separately authorized
  implementation phase: `[ ]`
- Reject or return for revision: `[ ]`
- Reviewer:
- Review date:
- Notes:
