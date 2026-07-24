# ORE Miner V3 — Research Roadmap

## Completed: Phase 1

- Historical replay selection.
- Outcome-isolated strategy evaluation.
- Reusable prepared replay batches.
- Deterministic fixed control.
- Reproducible seeded-random control.
- Replay-loader performance optimization.
- Random baseline distribution.
- Least-crowded decision timing sweep.

## Phase 2: Understand observable signals

1. Produce per-square descriptive statistics.
2. Visualize board-position win frequencies.
3. Measure congestion and allocation relationships.
4. Build only time-safe historical features for live-like evaluation.
5. Use chronological walk-forward train/test windows.
6. Score economic outcomes, not hit rate alone.

## Research rules

- Keep finalized outcomes outside strategy inputs.
- Preserve deterministic baselines.
- Compare every candidate with random controls.
- Distinguish descriptive/oracle analysis from deployable strategy logic.
- Record exact parameters and dataset versions.
- Prefer walk-forward validation over in-sample rankings.
