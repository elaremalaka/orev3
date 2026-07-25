# ORE Miner V3 Agent Instructions

Read `docs/rfcs/RFC-003B-HANDOFF.md` before changing datasets, features, analysis, modeling, backtesting, or inference.

## Core correctness rule

Every predictive feature must use only information available at or before the current observation.

Never use as model inputs:

- `winning_square`
- `won`
- finalized outcome fields
- future observations
- final board state
- outcome-enriched values
- replay fields unavailable during live inference

Outcome fields may be used only as labels or for evaluation.

## Feature architecture

Reusable features belong in:

`src/orev3/features/`

Features must:

- receive `FeatureContext`
- avoid parsing CSV rows directly
- register through `FeatureRegistry`
- declare a unique name
- declare a feature family
- declare exact output columns
- preserve deterministic column ordering
- handle ties explicitly

Do not use `mass` as a predictive feature. The audited replay dataset contains constant zero mass.

## Dataset invariants

Current canonical dataset:

- 439 rounds
- 33,956 observations
- 848,900 rows
- 25 square rows per observation

The feature dataset must preserve:

`round × observation × square`

Validate:

`rows == observations × 25`

## Testing

Run relevant tests before considering work complete.

At minimum:

`PYTHONPATH=src pytest -q tests/features`

Test:

- complete ties
- partial ties
- zero totals
- zero variance
- insufficient history
- first observations
- missing `slots_remaining`
- output collisions
- non-finite values

## Research discipline

Do not begin model training until expanded features pass a feature audit.

Do not use random row-level train/test splits. Keep all rows from a round together and preserve temporal order.

Prefer small, reviewable changes.

Do not commit generated CSV datasets unless explicitly requested.
