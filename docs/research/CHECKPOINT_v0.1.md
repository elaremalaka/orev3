# ORE Miner V3 — Research Checkpoint v0.1

**Date:** 2026-07-23  
**Milestone:** Phase 1 — Replay Infrastructure and Baseline Validation  
**Status:** Complete

## Objective

Establish a reproducible historical replay framework for evaluating ORE mining strategies without look-ahead bias, then validate it with deterministic and seeded-random controls.

## Architecture

Historical observations are resolved into strategy-safe `ReplayPoint` objects. A strategy receives only information available at the selected historical decision point. The finalized lifecycle outcome remains separate until after the decision has been frozen and passed to scoring.

```text
Historical round lifecycle
          |
          v
prepare_replay_batch()
          |
          v
PreparedReplayCase
  - ReplaySelection      -> strategy-visible
  - finalized lifecycle -> scoring-only
          |
          v
Strategy.evaluate(ReplayPoint)
          |
          v
Frozen StrategyDecision
          |
          v
score_evaluation()
          |
          v
Experiment metrics
```

### Stable architectural decisions

- Strategies receive only `ReplayPoint`.
- Finalized outcomes are unavailable during strategy evaluation.
- Replay preparation is performed once and reused across strategies.
- Random controls are reproducible through deterministic seeds.
- Fixed deterministic controls remain available for regression testing.
- Slot-distance tolerance is explicit and recorded for each replay case.

## Replay Performance Optimization

The replay loader previously reopened JSONL files and rescanned from line one for each snapshot reference.

Profiling showed:

- 33,956 `load_snapshot_reference()` calls.
- Approximately 75.5 million UTF-8 decode calls.
- Approximately 282 seconds total runtime.
- JSON decoding and model validation were not material bottlenecks.

A process-local cache was added so each source file is loaded once and snapshot references use direct line indexing.

| Metric | Before | After |
|---|---:|---:|
| Replay preparation | 278.868 s | 0.713 s |
| Total experiment runtime | ~279.8 s | 1.633 s |
| Preparation speedup | — | ~391x |
| Preparation reduction | — | ~99.74% |

Replay preparation is no longer a research bottleneck.

## Baseline Strategies

### Least-Crowded Top 4

Selects the four squares with the lowest miner counts at the replay point. Ties are resolved by square index and allocations are equal.

### Fixed Top 4

Permanent deterministic control that always selects:

```text
0, 1, 2, 3
```

This baseline is not derived from finalized outcomes.

### Seeded Random Top 4

Selects four of 25 squares reproducibly using a base seed combined with the round ID.

## Experiments Completed

### Random Baseline Distribution

Parameters:

```text
slots_remaining = 20
max_slot_distance = 3
random_seeds = 100
accepted_rounds = 437
```

Results:

| Metric | Result |
|---|---:|
| Least-crowded hits | 65 |
| Least-crowded hit rate | 14.87% |
| Random mean | 16.17% |
| Random median | 16.25% |
| Random minimum | 12.81% |
| Random maximum | 20.59% |
| Least-crowded percentile | 24% |
| Theoretical random rate | 16.00% |

The random distribution agrees with theoretical 4-of-25 coverage.

### Decision Timing Sweep

Parameters:

```text
slots_remaining = 5, 10, 15, 20, 25, 30, 35, 40
max_slot_distance = 3
random_seeds_per_timing = 100
```

| Slots | Rounds | LC Hits | LC Rate | Random Mean | Delta | Percentile |
|---:|---:|---:|---:|---:|---:|---:|
| 5 | 439 | 67 | 15.26% | 16.16% | -0.90 pp | 32% |
| 10 | 438 | 66 | 15.07% | 16.16% | -1.09 pp | 28% |
| 15 | 436 | 62 | 14.22% | 16.18% | -1.96 pp | 19% |
| 20 | 437 | 65 | 14.87% | 16.17% | -1.30 pp | 24% |
| 25 | 438 | 67 | 15.30% | 16.17% | -0.87 pp | 32% |
| 30 | 435 | 66 | 15.17% | 16.14% | -0.97 pp | 32% |
| 35 | 436 | 62 | 14.22% | 16.17% | -1.95 pp | 18% |
| 40 | 438 | 62 | 14.16% | 16.17% | -2.01 pp | 18% |

Average least-crowded hit rate across timings was approximately 14.78%, versus approximately 16.17% for random controls.

## Conclusions

### Validated

- The replay/scoring framework behaves consistently with theoretical random coverage.
- Finalized outcomes remain isolated from strategy evaluation.
- Prepared batches can be reused safely across many strategies and seeds.
- Replay preparation is fast enough for broad historical experimentation.

### Rejected as standalone hypotheses

- The four least-crowded squares outperform random selection.
- Moving the least-crowded decision earlier or later creates a consistent edge.

### Important limitation

These experiments evaluate winning-square coverage, not complete economic profitability. Future candidate strategies must also be evaluated using deployment cost, payout sharing, transaction costs, ORE value, and risk.

## Phase 2

The next research phase will study observable signals rather than proposing additional unsupported heuristics.

Priority order:

1. Historical square statistics.
2. Board-position heat maps.
3. Congestion and allocation correlations.
4. Motherlode-specific analysis.
5. Time-safe feature engineering.
6. Walk-forward predictive models.
7. Economic and risk-adjusted strategy evaluation.
