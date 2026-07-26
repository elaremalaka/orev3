# RFC-008 Economic-Threshold Approval Amendment

Status: **Approved**

Approval date: `2026-07-25`

This amendment resolves the final condition on RFC-008 approval. It uses only
the frozen pre-holdout rounds `342132` through `342570`, the approved
30-second decision rule, and the content-hashed artifacts in the RFC-008
approval package. No RFC-008 holdout data exist or were used.

## Frozen economic assumptions

Each active arm selects four squares, deploys 50,000 lamports in equal
12,500-lamport allocations, pays an assumed 5,000-lamport deploy fee, and pays
an assumed 5,000-lamport claim fee only after a positive reconstructed return.
Priority and failed-transaction fees are zero.

For a hit, reconstructed gross SOL is:

`12,500 × round total winnings ÷ final winning-square deployment`

using deterministic integer division. Deployment principal is a cost.
Motherlode ORE is reported separately and is not monetized. Base ORE is
unavailable. Excluding ORE value makes the SOL break-even calculation
conservative.

## Simple hit-rate approximation

Across the 439 frozen rounds, the mean gross return that one 12,500-lamport
winning-square allocation would have produced was 267,437.3667 lamports.

With hit probability `p`, approximate expected net is:

`p × mean gross − 55,000 − p × 5,000`

Therefore:

`p_break_even = 55,000 ÷ (267,437.3667 − 5,000) = 0.2095738`

Against the theoretical random top-four hit rate of 0.16, this requires an
improvement of 4.96 percentage points. This is only an approximation because
it treats hit value as independent of strategy and round.

## Reward-weighted break-even

The frozen candidate hit 75 of 439 rounds. Those hits generated 20,209,943
lamports of reconstructed gross SOL, or 269,465.9067 lamports per hit.
Preserving that empirical hit-value distribution gives:

`p_break_even = 55,000 ÷ (269,465.9067 − 5,000) = 0.2079663`

The corresponding improvement over 0.16 is 4.80 percentage points.

A 200,000-sample independent-round bootstrap with seed `20260725` gives a
97.5th-percentile break-even hit rate of 0.2090450, equivalent to +4.90
percentage points. Converting observed candidate misses in
lowest-value-first order requires 18 additional hits, a 21.18% candidate hit
rate and +4.78 points over the frozen random baseline's 72 hits.

## Decision

The most conservative calculated improvement is the simple approximation,
+4.96 percentage points. Rounded upward, the economically motivated minimum
would be +5 points.

The proposed +6-point observed paired improvement is strictly stronger and is
retained. It was not chosen to favor history: the frozen historical candidate
advantage was only +0.68 points and its reconstructed after-fee ROI was
negative.

A single hit-rate threshold is not sufficient for economic viability because
gross value varies by round and winning-square deployment. RFC-008 therefore
also retains all reward-weighted economic success conditions:

- reconstructed after-fee ROI greater than zero;
- lower two-sided 95% independent-round bootstrap ROI bound greater than zero;
  and
- one-sided paired economic randomization `p < 0.025` versus no-deploy.

The predictive and economic gates must both pass.

Machine-readable reproduction values are frozen in
`docs/research/rfc008/economic_threshold_v1.json`.
