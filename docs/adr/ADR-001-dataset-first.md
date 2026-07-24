# ADR-001: Dataset-First Research

**Status:** Accepted  
**Date:** 2026-07-23

## Decision

Replay is the authoritative historical reconstruction layer. Versioned datasets
are the primary interface for exploratory analysis and model development.

## Consequences

- Faster repeated analysis.
- Clearer separation between reconstruction and research.
- New replay work occurs only when new observable features are required.
