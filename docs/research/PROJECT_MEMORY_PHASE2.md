# ORE Miner V3 Project Memory — Phase 2

## Ratified Direction

ORE Miner V3 is now operated as a quantitative research platform.

The replay engine is considered stable infrastructure. New analysis should
consume versioned datasets instead of directly replaying history unless a new
observable feature must be extracted.

## Current Primary Dataset

```text
data/research/square_features_v1_slots_20.csv
```

Integrity results:

```text
Rows:                 10,925
Columns:              41
Source rounds:        439
Accepted rounds:      437
Rejected rounds:      2
Rows per round:       25
Winning rows/round:   1
```

Availability:

```text
square_sol_raw:                 unavailable
total_board_sol_raw:            unavailable
sol_share:                      unavailable
average_sol_per_miner_raw:      unavailable
round_motherlode_raw:           fully populated
```

## Permanent Rules

- No strategy without a supporting research report.
- Do not use labels or finalized outcomes as features.
- Do not treat full-history descriptive rankings as deployable signals.
- Do not optimize for hit rate without economic evaluation.
- Do not fill missing features by guessing.
- Preserve seeded-random and fixed controls.
- Preserve negative findings.

## Immediate Next Step

Implement and execute RFC-001: Exploratory Analysis of Square Features V1.
