# Research Documentation

## Artifact Types

### RFC

Defines a research question before implementation.

### Report

Records reproducible empirical output.

### Journal

Captures interpretation, decisions, and changes in direction.

### Checkpoint

Summarizes the stable state of the project at a milestone.

### Dataset Card

Documents the origin, schema, limitations, and intended use of a dataset.

---

### Discovery Session

Exploratory investigation of an archived research dataset.

Discovery Sessions generate observations, identify recurring patterns, and
produce candidate Research Questions.

### Research Backlog

Tracks operational improvements, future investigations, and deferred ideas that
are intentionally outside the current research focus.

See the [Research Backlog](backlog/RESEARCH-BACKLOG.md).

## Research Workflow

The research program follows a structured progression.

```
Observer Collection
        ↓
Dataset Build
        ↓
Archive Research Snapshot
        ↓
Discovery Session
        ↓
Observations
        ↓
Research Question
        ↓
Formal Analysis
        ↓
RFC (if required)
        ↓
Implementation
        ↓
Validation
```

Research is intended to be evidence-driven.

Observations precede hypotheses.

Hypotheses precede Research Questions.

Research Questions precede implementation.

---

## Repository Structure

Human-readable research documentation lives under `docs/research/`.

Machine-readable research artifacts are organized under
[`data/research/`](../../data/research/README.md).

Archived datasets are stored under:

```
data/research/snapshots/
```

Analysis outputs are stored under:

```
data/research/analyses/
```

Every local archived dataset should contain:

- replay dataset
- metadata
- snapshot README

Archived datasets are immutable.

Snapshot documentation may be tracked in Git. Generated dataset payloads,
machine-readable snapshot metadata, and analysis outputs remain ignored unless
a separately approved artifact-storage workflow is used.

---

## Current Research Program

Completed

- RQ-001 — Observer Persistence Validation
- RQ-002 — Post-Transition Finalization

Current Focus

- Discovery Session 1

Upcoming

- RQ-003 — Winning Square Predictability
- RQ-004 — Portfolio Containment Analysis
- RQ-005 — Economic Portfolio Optimization

Operational improvements and future investigations are tracked separately in
the [Research Backlog](backlog/RESEARCH-BACKLOG.md).
