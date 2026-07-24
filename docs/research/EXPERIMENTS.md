# ORE Miner V3 — Experiment Log

## EXP-001: Replay preparation profile

### Purpose

Identify why historical replay preparation required several minutes while strategy evaluation itself required less than one second.

### Finding

`load_snapshot_reference()` repeatedly reopened JSONL files and rescanned from the beginning. Roughly 75.5 million UTF-8 decode calls dominated runtime.

### Change

Cache source-file lines process-locally and resolve references through direct line indexing.

### Result

Replay preparation improved from 278.868 seconds to 0.713 seconds.

## EXP-002: Random baseline distribution

### Command

```bash
python -m orev3.experiments.random_baseline_distribution \
  --slots-remaining 20 \
  --max-slot-distance 3 \
  --seeds 100
```

### Result

- Accepted replay points: 437
- Least-crowded hit rate: 14.87%
- Random mean: 16.17%
- Random median: 16.25%
- Least-crowded percentile: 24%
- Theoretical random coverage: 16.00%

### Interpretation

The random controls validate basic scoring behavior. Least-crowded did not demonstrate an advantage.

## EXP-003: Decision timing sweep

### Command

```bash
python -m orev3.experiments.timing_sweep \
  --slots 5 10 15 20 25 30 35 40 \
  --max-slot-distance 3 \
  --seeds 100
```

### Result

Least-crowded underperformed the random mean at every tested timing. Its best deltas were still negative:

- 25 slots: -0.87 percentage points.
- 5 slots: -0.90 percentage points.
- 30 slots: -0.97 percentage points.

### Interpretation

Decision timing does not rescue least-crowded as a standalone ranking rule.

## Next experiment

Historical statistics for all 25 squares, including win frequency and strategy-visible miner/SOL characteristics. Historical winner-derived rankings must be labeled as descriptive or oracle analyses unless evaluated through a time-safe walk-forward process.
