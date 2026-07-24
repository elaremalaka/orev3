# ORE Miner V3 — Project Memory

## Current checkpoint

`checkpoint-v0.1`

Phase 1 is complete. The replay system is strategy-safe, reproducible, and fast enough for repeated historical research.

## Known-good facts

- Strategies receive only `ReplayPoint`.
- Finalized outcomes enter only after decisions are frozen.
- Replay source lines are cached process-locally.
- Replay preparation improved from 278.868 seconds to 0.713 seconds.
- Random 4-of-25 controls average approximately the theoretical 16% coverage.
- Least-crowded underperformed random at every tested decision timing.
- Fixed Top 4 is a deterministic control selecting squares 0, 1, 2, and 3.

## Do not silently revisit

- Do not pass finalized lifecycle data into `Strategy.evaluate()`.
- Do not use a full-history square ranking as though it were deployable.
- Do not interpret hit rate alone as profitability.
- Do not remove reproducible controls when adding candidate strategies.
- Do not rescan JSONL files per snapshot reference.

## Next task

Build a historical square-statistics experiment, clearly separating descriptive full-history statistics from time-safe predictive features.
