# ORE Miner V3 Research Backlog

Items remain in the backlog until intentionally promoted to a Research
Question, RFC, or implementation task.

## Purpose

This document records operational improvements, research ideas, investigations,
and future engineering work that are intentionally deferred.

Items in this backlog are **not** active Research Questions (RQs) and are
**not** RFCs.

They exist so that good ideas are not forgotten while allowing the current
research program to remain focused.

---

## Status Definitions

- **Backlog** — Recorded but not yet investigated.
- **Investigating** — Currently being explored.
- **Ready** — Well understood and ready for implementation or formal research.
- **Completed** — Finished.

---

## Priority Definitions

- **Low**
- **Medium**
- **High**
- **Critical**

---

# RB-001 — Dataset Build Performance

**Status:** Backlog

**Priority:** Medium

**Category:** Operational Improvement

**Observed:** 2026-08-10

## Summary

A full dataset build using:

```bash
python -m orev3.dataset.build
```

appeared to stall for more than 90 minutes while using negligible CPU.

The equivalent build using:

```bash
python -m orev3.dataset.build --skip-enrichment
```

completed normally.

## Questions

- Where is enrichment spending its time?
- Is enrichment blocked waiting on RPC?
- Are retries occurring indefinitely?
- Is enrichment processing outcomes serially?
- Would batching improve performance?
- Should enrichment expose progress?

## Desired Outcome

Produce a reliable enrichment pipeline that:

- provides progress reporting;
- exposes current phase;
- detects stalled RPC requests;
- remains deterministic.

## Blocking

No.

Exploratory research can continue using
`--skip-enrichment`.

Production-quality dataset generation should investigate this before large
releases.

---

# RB-002 — Dataset Build Progress Reporting

**Status:** Backlog

**Priority:** Medium

**Category:** User Experience

**Observed:** 2026-08-10

## Summary

Long-running dataset builds currently provide little visibility into their
progress.

Large builds may appear stalled even while useful work is occurring.

## Desired Experience

Example:

```text
ORE Miner V3 — Dataset Build

Reading Observer Data
██████████████████ 100%

Building Replay Lifecycles
██████████████████ 100%

RFC-012 Reconciliation
██████████████████ 100%

Outcome Enrichment
███████░░░░░░░░░░ 41%

Current Round: 360842
RPC Requests: 5,243 / 12,412

Writing Dataset
██████████░░░░░░░ 63%
```

## Questions

- What stages should be reported?
- Can total work be estimated?
- Can progress remain deterministic?
- Should elapsed and estimated remaining time be shown?

## Blocking

No.

Operational usability improvement.

---

# RB-003 — Partial-Start Lifecycle Investigation

**Status:** Backlog

**Priority:** Medium

**Category:** Research Investigation

**Observed:** 2026-08-10

## Summary

RFC-012 validation identified a significant number of `partial_start`
lifecycles.

The validation analysis suggested that this pattern may correlate with the
synchronous finalized-history scan that occurs after current-round finalized
persistence.

This has not been proven.

## Questions

- Why do partial-start lifecycles occur?
- Are they correlated with current-round finalized persistence?
- Does the finalized-history scan introduce observable latency?
- Would caching or another implementation reduce partial-start frequency?
- Does this affect replay quality or only dataset coverage?

## Desired Outcome

Determine the root cause of partial-start lifecycles.

If a performance bottleneck exists, quantify it before considering any
architectural or implementation changes.

## Blocking

No.

Current replay correctness appears unaffected.

---

# RB-004 — RFC-012 Effectiveness Report

**Status:** Backlog

**Priority:** High

**Category:** Research

**Observed:** 2026-08-10

## Summary

After approximately one week of RFC-012 collection, produce the first formal
effectiveness report for the completed implementation.

## Proposed Contents

- Replay rounds
- Complete vs incomplete rounds
- Current-round observed outcomes
- Post-transition predecessor outcomes
- Total locally observed outcomes
- Enriched outcomes
- Missing outcomes
- Enrichment avoided
- Terminal-disposition distribution
- Transition statistics
- Architectural validation summary
- Remaining limitations
- Candidate future improvements

## Desired Outcome

Determine whether RFC-012 achieved its objective of increasing locally observed
finalized outcomes while preserving replay purity and deterministic behavior.

## Blocking

Wait until sufficient post-RFC-012 data has been collected.

---

# RB-005 — Research Roadmap

**Status:** Backlog

**Priority:** Medium

**Category:** Documentation

**Observed:** 2026-08-10

## Summary

Create a permanent roadmap describing the research direction of ORE Miner V3.

The roadmap should identify completed, active, and proposed Research Questions
along with their dependencies.

## Proposed Structure

Completed

- RQ-001 — Observer Persistence Validation
- RQ-002 — Post-Transition Finalization

Proposed

- RQ-003 — Winning Square Predictability
- RQ-004 — Portfolio Containment Analysis
- RQ-005 — Economic Portfolio Optimization
- RQ-006 — Capital Migration
- RQ-007 — Miner Migration
- RQ-008 — Motherlode Influence
- RQ-009 — Behavioral Clustering

## Desired Outcome

Provide a long-term research roadmap that guides future investigation without
requiring immediate implementation.

## Blocking

None.

---

# RB-006 — Research Dataset Versioning

**Status:** Backlog

**Priority:** Medium

**Category:** Research Infrastructure

**Observed:** 2026-08-10

## Summary

Formalize the process for archiving research datasets so that every Research
Question references an immutable dataset snapshot.

## Goals

- Standard snapshot naming convention
- Snapshot metadata
- Dataset provenance
- Reproducible research
- Cross-version comparison

## Desired Outcome

Every Research Question should state exactly which archived dataset(s) it used.

Research results should remain reproducible even after future dataset builds.

## Blocking

None.
