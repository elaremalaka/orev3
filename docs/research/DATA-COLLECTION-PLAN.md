# ORE Miner V3 Data Collection Plan

## Decision

Continue collecting data while analysis proceeds. Do not wait for a "complete"
dataset before running RFCs, and do not treat the current 437 rounds as final
evidence.

## Near-term targets

- 1,000 accepted rounds: first meaningful stability review
- 2,500 accepted rounds: stronger conditional and subgroup analysis
- 5,000 accepted rounds: preferred target before trusting narrow interaction
  rules with meaningful capital

These are review milestones, not guarantees of statistical sufficiency.

## Collection priorities

1. Preserve complete board snapshots at consistent replay horizons.
2. Preserve finalized winning square for every accepted round.
3. Keep source timestamp, RPC slot, start slot, end slot, and replay distance.
4. Avoid changing feature definitions silently.
5. Record observer downtime and known data gaps.
6. Continue searching for replay-visible per-square SOL data without fabricating
   unavailable values.
7. If multiple snapshot horizons are collected, keep them separately versioned.

## Quality checks

Track:

- source rounds
- accepted and rejected rounds
- rejection reason
- exact-slot-match rate
- replay-slot-distance distribution
- missingness by field
- duplicate round IDs
- round coverage by hour and day
- schema and feature version

## Research discipline

New data should be treated as future chronological evidence. Avoid repeatedly
tuning a rule on the entire expanding dataset and then reporting the same data
as validation.

A practical policy is:

- development window: earlier rounds
- validation window: later untouched rounds
- final confirmation window: newest untouched rounds
