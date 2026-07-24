# RFC-001: Exploratory Analysis of Square Features V1

**Status:** Ratified  
**Date:** 2026-07-23  
**Owner:** ORE Miner V3 Research

## Objective

Produce the first reproducible exploratory analysis of:

```text
data/research/square_features_v1_slots_20.csv
```

This RFC is descriptive. It does not create or approve a strategy.

## Research Questions

1. Do observed win rates differ materially by square?
2. Does average miner congestion differ by square?
3. Do corners, edges, and interior positions behave differently?
4. Is miner count associated with winning?
5. Are orthogonal-neighbor congestion features associated with winning?
6. Which dataset fields are populated and suitable for later modeling?

## Inputs

- `square_features_v1_slots_20.csv`
- Corresponding dataset manifest

Known input properties:

- 437 accepted rounds.
- 10,925 rows.
- 25 square rows per round.
- One winner per round.
- 41 columns.
- Per-square SOL-derived fields are empty in V1.

## Deliverables

### Code

```text
src/orev3/analysis/square_statistics.py
```

### Generated artifacts

```text
reports/research/square_statistics_v1.md
results/research/square_statistics_v1.csv
results/research/square_heatmap_v1.csv
results/research/geometry_statistics_v1.csv
results/research/feature_correlations_v1.csv
```

## Required Analyses

### Dataset integrity

- Row count.
- Unique round count.
- Rows per round.
- Winners per round.
- Missingness by field.

### Square statistics

For every square:

- rounds observed,
- wins,
- empirical win rate,
- expected wins under uniform probability,
- difference from 4% square-level expectation,
- average and median miner count,
- average miner share,
- average neighbor miner count.

### Geometry statistics

Compare:

- corners,
- edges,
- interior non-center squares,
- center square.

### Congestion statistics

Compare winning and losing rows using:

- miner count,
- miner share,
- miner rank,
- empty-square indicator,
- top-four and bottom-four indicators,
- orthogonal-neighbor congestion.

### Correlations

Calculate descriptive correlations between numeric strategy-visible fields and
the `won` label.

Correlations are exploratory and must not be interpreted as deployable evidence
without chronological validation.

## Acceptance Criteria

- All 25 squares appear exactly once in square summary output.
- Aggregate wins equal 437.
- Heatmap output is a complete 5x5 board.
- Missing SOL fields are reported and excluded from numeric conclusions.
- Generated reports identify descriptive findings separately from predictive
  claims.
- Runtime is below five seconds on the current dataset.
- The script can be rerun from the repository root.
- Outputs contain dataset and feature version metadata.

## Non-Goals

- Strategy creation.
- Model training.
- Replay changes.
- SOL feature reconstruction.
- Causal claims.
- Live deployment recommendations.

## Decision Gate

RFC-002 may investigate congestion or positional hypotheses only after the
RFC-001 report is reviewed.

A strategy may be proposed only if a later time-safe report supports it.
