# ADR-005: Production Miner Promotion Gate

**Status:** Accepted  
**Date:** 2026-07-23

## Decision

A candidate becomes a production miner only after passing:

1. data and leakage review,
2. out-of-sample walk-forward evaluation,
3. full economic and drawdown review,
4. paper execution,
5. controlled live execution,
6. wallet-level reconciliation,
7. operational reliability review.

## Consequences

Backtest success alone cannot authorize unrestricted live deployment.
