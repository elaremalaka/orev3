# Dataset Card: square_features_v1

## Identity

```text
Dataset version: square_features_v1
CSV: data/research/square_features_v1_slots_20.csv
Manifest: data/research/square_features_v1_slots_20.manifest.json
```

## Build Summary

- Source rounds: 439
- Accepted rounds: 437
- Rejected rounds: 2
- Rows: 10,925
- Columns: 41
- Decision point: 20 slots remaining
- Expected rows: 10,925
- Build runtime: 1.493 seconds

## Integrity

- 25 rows for every accepted round.
- Exactly one winning square for every accepted round.

## Known Limitations

The following fields are unavailable in V1:

- `square_sol_raw`
- `total_board_sol_raw`
- `sol_share`
- `average_sol_per_miner_raw`
- SOL-derived neighbor statistics

`round_motherlode_raw` is fully populated.

Unavailable values must not be reconstructed by assumption.
