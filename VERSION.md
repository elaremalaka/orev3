# ORE Miner V3

# Version 1.0

**Release Date:** July 31, 2026

---

## Vision

ORE Miner V3 is a deterministic, protocol-faithful research platform for the ORE protocol.

Its purpose is to study mining strategies using historical replay, protocol-faithful deployment simulation, and deterministic economic evaluation before any paper or live execution.

Version 1.0 marks the completion of the platform itself.

Future development will be driven primarily by experimental findings rather than architectural expansion.

## Official Protocol Compatibility

Version 1.0 is pinned to the official ORE protocol revision:

`3112ab78a64f92892a70d5d4cbd17e1d14b1c2fe`

This revision already includes the official ORE V4 migration. Compatibility is determined by the exact source revision rather than marketing version labels.

---

# Major Milestones

## Governance

- Repository Architecture
- RFC-008 — Production Governance
- RFC-009 — Continuation Governance
- RFC-010 — Strategy Laboratory
- RFC-011 — ORE Deployment Economics

## Production

- Observer
- Durable finalized outcome persistence
- Historical collection
- Dataset Builder
- Dataset Validator
- Dataset Inspector

## Research

- Replay Engine
- Strategy Laboratory
- Baseline Research Suite
- Experiment CLI

## Economic Simulation

- Economic Scenario
- Allocation Materializer
- Protocol Constraint Model
- Transaction & Inclusion Model
- ORE Settlement Engine
- Economic Simulation Runner
- Economic Metrics Engine
- Economic Simulation Record
- Economic CLI

---

# Version 1.0 Architecture

```
Historical Collection
        │
        ▼
Replay Engine
        │
        ▼
Strategy Laboratory
        │
        ▼
Protocol-Faithful Economic Simulation
        │
        ▼
Economic Experiment Records
```

---

# Current Status

Version 1.0 completes the foundational research platform.

The repository now supports:

- deterministic historical replay;
- protocol-faithful deployment simulation;
- protocol-faithful economic simulation;
- reproducible experiment records.

Future work is expected to focus on:

- strategy research;
- paper execution;
- live execution;

rather than further architectural expansion.

---

> *Build the platform once. Learn from it forever.*
