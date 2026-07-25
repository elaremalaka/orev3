# ORE Miner V3 — RFC-003B Handoff

## Current phase

Completed:

- RFC-001
- RFC-002
- RFC-002B
- RFC-003A — Canonical Observation Dataset
- RFC-003A.5 — Observation Dataset Exploration
- RFC-003B initial feature framework

Current milestone:

- RFC-003B.1 — Relative and Temporal Feature Expansion
- Feature auditing before model training

Future milestone:

- RFC-004 — Model training and walk-forward evaluation

## Canonical observation dataset

- 439 rounds
- 33,956 observations
- 848,900 rows
- exactly 25 square rows per observation
- 437 complete rounds
- 2 partial rounds
- 58 observed outcomes
- 381 enriched outcomes

Dataset:

`data/research/observation_dataset_v1.csv`

Manifest:

`data/research/observation_dataset_v1.manifest.json`

`slots_remaining` is missing only at the beginning of some rounds:

- first observation: 176
- second observation: 7
- middle, late, and final observations: 0

Treat this as expected early-round unavailability.

## Mass-field audit

The replay `mass` field is unusable in the current dataset.

Findings:

- identical mass vector across all observations: 439 rounds
- rounds where mass changes: 0
- observed mass values: zero

Do not use `mass` as a predictive feature unless a real contemporaneous source is identified and validated.

## Modeling unit

Each training example is:

`round_id × observation_index × square_index`

The label is:

`won = 1 if square_index == winning_square else 0`

The winner is the label, not the object used to engineer features.

Every predictive feature must be computable using information available at or before the current observation.

## RFC-003B architecture

Canonical Observation Dataset
→ FeatureContext
→ FeatureRegistry
→ FeaturePipeline
→ Square Feature Dataset
→ Feature Audit
→ Model Training
→ Live Inference

Reusable feature code belongs in:

`src/orev3/features/`

Research and diagnostics belong in:

`src/orev3/analysis/`

Dataset construction belongs in:

`src/orev3/datasets/`

## Implemented framework

Implemented:

- `src/orev3/features/types.py`
- `src/orev3/features/context.py`
- `src/orev3/features/base.py`
- `src/orev3/features/registry.py`
- `src/orev3/features/pipeline.py`
- `src/orev3/features/raw.py`
- `src/orev3/features/relative.py`
- `src/orev3/features/temporal.py`
- `src/orev3/features/__init__.py`

Dataset builder:

`src/orev3/datasets/build_square_feature_dataset.py`

Tests:

`tests/features/test_feature_framework.py`

## Current feature dataset

Dataset:

`data/research/square_feature_dataset_v1.csv`

Manifest:

`data/research/square_feature_dataset_v1.manifest.json`

Build results:

- 439 rounds
- 33,956 observations
- 848,900 rows
- 13 feature columns
- 25 rows per observation
- approximately 22 seconds runtime

## Existing features

Raw:

- miner_count
- deployed_lamports
- reward_raw

Relative:

- miner_share
- deployed_share
- miner_average_rank
- deployed_average_rank
- miner_ratio_to_leader
- deployed_ratio_to_leader

Temporal proof of concept:

- miner_delta_1
- deployed_delta_1
- reward_delta_1
- has_previous_observation

Ranking uses average rank for ties.

A complete 25-way tie gives every square rank 13.0.

## Immediate next task

Implement the first RFC-003B.1 increment:

1. Inspect the existing framework and tests.
2. Preserve current interfaces unless a concrete bug requires a change.
3. Add reusable board-summary calculations.
4. Add expanded relative features.
5. Add tests for:
   - zero-total boards
   - complete ties
   - partial ties
   - zero standard deviation
   - leader ratios
   - feature-column uniqueness
   - non-finite output
6. Run all feature tests.
7. Rebuild the feature dataset.
8. Add the feature-audit foundation.
9. Do not begin model training.

## Future evaluation constraints

Do not randomly split square rows.

Keep all rows from a round in the same partition.

Use chronological, grouped, or walk-forward evaluation.

Track metrics such as:

- log loss
- Brier score
- top-1 hit rate
- top-3 hit rate
- top-5 hit rate
- mean reciprocal rank
- calibration
- simulated economic return after costs
