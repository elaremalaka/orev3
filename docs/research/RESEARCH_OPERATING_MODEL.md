# ORE Miner V3 Research Operating Model

**Ratified:** 2026-07-23  
**Status:** Active

## Core Philosophy

> Replay once. Analyze forever.

The project will no longer lead with intuition-based strategy construction.
Future strategies must emerge from observable, measured, and reproducible
research findings.

## Required Research Sequence

Every new strategy idea must follow this sequence:

1. Define a research question.
2. Identify the dataset and observable inputs.
3. Produce a reproducible analysis.
4. Record the result in a research report.
5. State the supported or rejected hypothesis.
6. Build a candidate strategy only when evidence supports it.
7. Validate the candidate chronologically.
8. Evaluate complete economics and risk.
9. Paper deploy before live deployment.

## Strategy Admission Rule

No new strategy may be added unless it points to a research report that
justifies its existence.

Exceptions are allowed only for permanent controls used for regression or
benchmarking, such as seeded-random and fixed deterministic baselines.

## Dataset Rules

- Datasets are immutable after publication.
- Every dataset must include schema, feature, and dataset versions.
- Every generated dataset must include a manifest.
- Labels must be visibly separated from strategy-visible features.
- Missing fields remain missing rather than being guessed or inferred.
- New dataset versions are created when feature semantics change.

## Analysis Rules

- Analysis modules consume datasets rather than replay history.
- Descriptive and oracle analyses must be labeled clearly.
- Full-history statistics cannot be treated as deployable features.
- Statistical uncertainty and sample size must be reported.
- Negative results are preserved as project knowledge.

## Model Rules

- Chronological train/test splits are mandatory.
- Walk-forward evaluation is preferred.
- Randomized splits are not sufficient for strategy approval.
- Model performance must be compared with permanent baselines.
- Feature importance does not by itself establish causality.

## Documentation Rules

### RFCs

Describe planned research work, inputs, outputs, hypotheses, and acceptance
criteria.

### Reports

Record generated results and conclusions.

### Checkpoints

Capture stable milestones and validated project state.

### Project Memory

Records current facts, rejected ideas, and architectural decisions that should
not be revisited without new evidence.

## Current Project State

Phase 1 established and validated the replay framework.

Phase 2 begins with the immutable dataset:

```text
data/research/square_features_v1_slots_20.csv
```

Validated properties:

- 439 source rounds.
- 437 accepted rounds.
- 2 rejected rounds.
- 25 rows per accepted round.
- 10,925 total rows.
- Exactly one winner per round.
- 41 columns.
- Per-square SOL fields are currently unavailable.
- Motherlode is populated for all rows.

The immediate next task is RFC-001: exploratory analysis of
`square_features_v1`.
