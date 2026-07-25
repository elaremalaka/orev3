# RFC-002: Conditional Congestion and Geometry Analysis

## Status

Implemented for exploratory review.

## Motivation

RFC-001 showed weak unconditional linear relationships and descriptive
differences across squares and geometry. RFC-002 tests whether useful patterns
appear only under specific within-round congestion conditions.

## Hypotheses

1. Winning probability may vary non-monotonically with miner rank.
2. Geometry may interact with congestion.
3. Neighbor congestion may contain information not captured by square
   congestion alone.
4. A moderate-congestion region may outperform both extremes.

## Scope

This RFC produces:

- miner-rank bucket statistics
- within-round congestion quintiles
- geometry × congestion tables
- neighbor-congestion quintiles
- geometry × rank tables
- Wilson 95% descriptive confidence intervals

## Out of scope

- strategy implementation
- live deployment
- payout economics
- transaction fees
- causal claims
- machine learning

## Promotion criteria

A pattern advances to chronological testing only if it is:

- adequately sampled
- practically meaningful
- stable across time
- not driven by one square
- implementable in the miner
