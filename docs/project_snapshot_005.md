# ORE Miner V3 — Project Snapshot 005

## Milestone

ORE Miner V3 has completed the foundational data, historical reconstruction, replay, and strategy-interface layers.

The system can now:

1. Observe live ORE protocol state.
2. Persist immutable raw snapshots.
3. Normalize historical schema versions.
4. Assemble per-round lifecycle histories.
5. Enrich finalized round outcomes.
6. Persist a complete historical round index.
7. Replay point-in-time strategy-visible state without outcome leakage.
8. Evaluate strategies through a common Strategy Lab interface.

---

## Historical Dataset

The validated historical dataset contains:

- 33,956 normalized snapshots
- 439 assembled rounds
- 0 malformed source records in the overnight dataset
- 58 outcomes observed directly during collection
- 381 outcomes enriched after finalization
- 0 missing finalized outcomes
- 0 unavailable finalized outcomes
- 0 failed enrichment attempts

The persistent derived dataset is:

data/derived/round_lifecycles_v1.jsonl

The dataset manifest is:

data/derived/round_lifecycles_v1.manifest.json

Derived data remains local and is not committed to Git.

---

## Outcome Provenance

Finalized outcomes distinguish between:

observed

and:

enriched

Observed outcomes were captured in the historical observation stream.

Enriched outcomes were fetched later and exist only for scoring and analysis.

Enriched outcomes must never be exposed to a strategy during historical replay.

---

## Replay Engine

The Replay Engine reconstructs strategy-visible historical state.

Given:

- round_id
- requested slots remaining

the Replay Engine selects the closest observed RPC slot that does not exceed the target decision slot.

This prevents look-ahead bias.

Example:

Requested:

20 slots remaining

Observed:

21 slots remaining

Result:

Valid replay point.

A replay tolerance system was added.

Example:

Requested:

20 slots remaining

Observed:

27 slots remaining

Maximum allowed distance:

3 slots

Result:

within_tolerance = false

Low-precision replay points remain reproducible but can be excluded by future experiments.

---

## RPC Slot Regressions

RPC slot regressions remain preserved in raw data.

Replay selection uses the highest observed RPC slot that does not exceed the requested decision boundary.

This avoids selecting later/future protocol state.

RPC slot regressions are treated as data-quality information rather than modified or deleted.

---

## Strategy Lab Foundation

A common Strategy interface now exists.

Every strategy receives only:

ReplayPoint

Strategies do not receive:

- finalized outcome
- winning square
- final reward state
- enriched historical outcome data

Each strategy returns a structured:

StrategyDecision

A decision contains:

- strategy name
- strategy version
- participate or skip action
- square allocations
- optional confidence
- reason
- metadata

This provides a stable interface for future strategy experimentation.

---

## Baseline Strategy

The first Strategy Lab baseline is:

least_crowded_top4_equal

The baseline:

1. Reads miner counts from the ReplayPoint.
2. Ranks all 25 squares by miner count.
3. Selects the four least-crowded squares.
4. Splits allocation weight equally.

This baseline exists to validate Strategy Lab architecture.

It is not considered an optimized mining strategy.

---

## Architecture Progress

Observer:

VALIDATED

Snapshot Collector:

VALIDATED

Historical Reader:

VALIDATED

Round Lifecycle Assembler:

VALIDATED

Finalized Outcome Enricher:

VALIDATED

Historical Dataset Persistence:

VALIDATED

Replay Engine Foundation:

VALIDATED

Strategy Lab Foundation:

VALIDATION IN PROGRESS

Decision Engine:

NOT STARTED

Portfolio Simulator:

NOT STARTED

Paper Miner:

NOT STARTED

Live Miner:

NOT STARTED

Adaptive Strategy Layer:

NOT STARTED

---

## Architectural Flow

Solana RPC
↓
Observer
↓
Immutable Raw Snapshots
↓
Historical Reader
↓
Round Lifecycle Assembler
↓
Finalized Outcome Enricher
↓
Persistent Historical Dataset
↓
Replay Engine
↓
Strategy Lab
↓
Future Decision Engine
↓
Future Portfolio Simulator
↓
Future Paper Miner
↓
Future Live Miner

---

## Security

The repository security policy remains mandatory.

The following must never be committed:

- private keys
- wallet seed phrases
- passwords
- API keys
- RPC credentials
- authentication tokens
- personal information
- confidential information

Private RPC configuration remains local through:

ORE_RPC_URL

Raw and derived datasets remain excluded from Git.

---

## Next Milestone

After Strategy Lab validation, the next major step is:

Strategy Experiment Runner and Scoring Foundation

This system will:

1. Run one or more strategies across many historical rounds.
2. Select point-in-time replay states.
3. Reject replay points outside configured tolerance.
4. Record structured strategy decisions.
5. Reveal finalized outcomes only after decisions are complete.
6. Score decisions against actual outcomes.
7. Compare strategies using consistent metrics.

This will be the first layer that allows systematic strategy research across the V3 historical dataset.

