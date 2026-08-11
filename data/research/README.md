# ORE Miner V3 Research Data

## Purpose

This directory contains machine-readable research artifacts produced by
ORE Miner V3.

Human-readable documentation belongs under
[`docs/research/`](../../docs/research/README.md).

---

## Directory Structure

### [`snapshots/`](snapshots/rfc012-validation-48hr/README.md)

Immutable archived datasets used for research.

Snapshots should never be modified after creation.

Each local snapshot contains:

- replay dataset
- metadata
- snapshot README

Snapshot README files may be reviewed in Git. Dataset payloads and their
machine-readable metadata remain ignored unless a separately approved
artifact-storage workflow is used. This keeps source commits limited to the
snapshot workflow and human-readable provenance.

Example:

```
snapshots/
    rfc012-validation-48hr/
    rfc012-validation-1week/
    rq003-baseline/
```

---

### [`analyses/`](analyses/README.md)

Intermediate and final analysis artifacts.

Subdirectories are organized by analysis domain.

Current categories:

- baseline/
- datasets/
- economics/
- features/
- strategy/
- validation/

Analysis outputs are reproducible generated artifacts and remain ignored by
Git. Their organization under this directory does not change historical paths
embedded in immutable manifests or reports; those paths remain provenance.

---

### [`exports/`](exports/README.md)

Reserved for user-facing exported research artifacts.

Examples may include:

- CSV exports
- presentation datasets
- external reports

---

## Research Workflow

1. Collect Observer data.
2. Build the dataset.
3. Verify dataset health.
4. Archive a research snapshot.
5. Perform discovery and exploration.
6. Generate analysis artifacts.
7. Formalize Research Questions.
8. Produce reports.

---

## Guiding Principle

Snapshots are immutable.

Analyses may be regenerated.

Reports summarize findings.

Raw Observer data remains the authoritative source.

---

## Repository Boundary

This directory structure organizes research artifacts without changing CLI
defaults, RFC requirements, or application behavior. Any migration of
implementation-owned paths requires a separately authorized implementation
change.
