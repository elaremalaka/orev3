# RFC-010 Implementation Plan

**Status:** Approved for Implementation

This document defines the implementation roadmap for RFC-010.

Unlike RFC-010, this document is an engineering execution plan.

RFC-010 remains the authoritative architecture specification.

This implementation plan defines only the order in which RFC-010 shall be implemented.

Every implementation phase shall preserve the RFC-010 architecture.

No implementation phase may broaden the RFC without explicit architectural approval.

---

# Development Principles

Every implementation phase shall:

- preserve RFC-010 architecture;
- remain deterministic;
- compile successfully;
- include comprehensive unit tests;
- leave the repository in a releasable state.

Each phase ends only after:

- implementation is complete;
- tests pass;
- repository validation passes;
- worktree is clean;
- implementation is reviewed.

Implementation shall proceed strictly in order.

Later phases may depend upon earlier phases.

Earlier phases may not depend upon later phases.

---

# Phase 1 — Core Strategy Interfaces

## Objective

Establish the immutable public interfaces that define the Strategy Lab.

This phase creates the contracts that every future strategy and Strategy Lab component will use.

No replay, deployment, evaluation, metrics, persistence, or experiment execution shall be implemented during this phase.

---

## Deliverables

Implement the following public models:

- DecisionContext
- Strategy interface
- RankedCandidate
- RankedCandidateSet
- Explanation

These models become the stable public API for RFC-010.

---

## Responsibilities

### DecisionContext

Provide an immutable representation of all information historically available immediately before a decision.

DecisionContext shall never expose:

- future information;
- replay implementation details;
- mutable state.

---

### Strategy

Define the abstract strategy lifecycle.

Strategies shall support:

- initialize()
- choose(context)
- update(result)
- finalize()

Strategies may maintain deterministic internal state.

Strategies shall never:

- allocate capital;
- evaluate themselves;
- access persistence;
- communicate externally.

---

### RankedCandidate

Represents one candidate selected by a strategy.

Contains:

- square identifier;
- preference score;
- optional structured explanation.

Preference scores express ordering only.

---

### RankedCandidateSet

Immutable ordered collection of RankedCandidates.

Represents the complete preference ordering returned by a strategy.

---

### Explanation

Immutable strategy-owned explanation artifact.

The framework stores explanations without interpreting them.

Structured explanations exist to support:

- debugging;
- experiment review;
- visualization;
- future research.

---

## Out of Scope

Phase 1 shall not implement:

- Replay Engine integration.
- Experiment Runner.
- Deployment Models.
- Evaluator.
- Metrics Engine.
- Experiment Registry.
- Historical replay.
- Strategy implementations.

---

## Definition of Done

Phase 1 is complete when:

- all public interfaces exist;
- interfaces are immutable where appropriate;
- strategy lifecycle is defined;
- comprehensive unit tests pass;
- Python compilation passes;
- repository validation passes;
- worktree is clean.

---

# Phase 2 — Experiment Runner

## Objective

Implement the deterministic experiment execution framework.

This phase connects the Replay Engine to strategies through the immutable interfaces established in Phase 1.

The Experiment Runner becomes responsible for orchestrating replay execution.

No Deployment Models, Evaluator, Metrics Engine, or Experiment Registry shall be implemented during this phase.

---

## Deliverables

Implement:

- ExperimentRunner
- ExperimentConfiguration
- Strategy lifecycle orchestration
- Replay integration
- Deterministic experiment execution

The Experiment Runner shall execute strategies over historical replay data.

---

## Responsibilities

### Experiment Runner

The Experiment Runner is responsible for:

- loading replay datasets;
- constructing Decision Context objects;
- initializing strategies;
- invoking strategy decisions;
- providing historical outcomes back to strategies;
- advancing deterministic strategy state;
- executing replay sequentially.

The Experiment Runner is orchestration only.

It shall never:

- allocate capital;
- compute mining rewards;
- calculate metrics;
- produce reports.

---

### Strategy Lifecycle

Strategies shall execute according to the following deterministic lifecycle.

```
initialize()

↓

for each replayed round

↓

DecisionContext

↓

choose()

↓

historical outcome revealed

↓

update()

↓

repeat

↓

finalize()
```

The Strategy Lab shall guarantee that every strategy observes identical replay ordering.

---

### Replay Integration

Replay integration shall expose only immutable Decision Context objects.

The Replay Engine shall remain the sole authority responsible for reconstructing historical state.

The Experiment Runner shall never reconstruct replay state independently.

---

## Determinism Requirements

The Experiment Runner shall guarantee:

- deterministic replay ordering;
- deterministic strategy execution;
- deterministic strategy state evolution;
- deterministic replay completion.

Running the same strategy against the same replay dataset shall always produce identical decisions.

---

## Out of Scope

Phase 2 shall not implement:

- Deployment Models;
- Capital Allocation;
- Evaluator;
- Metrics Engine;
- Experiment Registry;
- Experiment Reports;
- Historical reward computation.

---

## Definition of Done

Phase 2 is complete when:

- Experiment Runner executes replay successfully;
- strategies complete their full lifecycle;
- deterministic replay is verified;
- identical replay produces identical decisions;
- comprehensive unit tests pass;
- Python compilation passes;
- repository validation passes;
- worktree is clean.

---

# Phase 3 — Deployment Models

## Objective

Implement the Deployment Model framework.

Deployment Models convert strategic preference into capital allocation.

This phase intentionally separates **decision quality** from **capital allocation**.

Strategies determine *where* to mine.

Deployment Models determine *how much* to mine.

---

## Deliverables

Implement:

- DeploymentModel interface
- CapitalAllocation model
- Equal Weight deployment
- Fixed Budget deployment

Deployment Models shall operate exclusively on Ranked Candidate Sets.

---

## Responsibilities

### Deployment Model

A Deployment Model receives:

- Ranked Candidate Set
- Experiment Configuration

It returns:

- Capital Allocation

Deployment Models never:

- modify strategy preferences;
- reconstruct replay state;
- evaluate historical outcomes;
- calculate metrics.

---

### Capital Allocation

Capital Allocation represents the deployment decision.

Each allocation contains:

- selected square;
- allocation amount;
- allocation weight;
- deployment metadata.

Capital Allocation becomes the sole input to the Evaluator.

---

### Equal Weight

Equal Weight distributes available capital evenly across all selected candidates.

---

### Fixed Budget

Fixed Budget allocates a fixed amount of capital per replayed round according to strategy preferences.

The total deployed capital remains constant across all replayed rounds.

---

## Architectural Principles

Deployment Models express **conviction**, not **preference**.

Strategies remain unaware of Deployment Models.

Deployment Models remain unaware of strategy implementation details.

The same strategy shall produce identical Ranked Candidate Sets regardless of which Deployment Model is later selected.

Likewise, the same Deployment Model shall produce deterministic Capital Allocations when given identical Ranked Candidate Sets.

---

## Out of Scope

Phase 3 shall not implement:

- historical reward computation;
- Evaluator;
- Metrics Engine;
- Experiment Registry;
- Experiment Reports;
- portfolio optimization;
- Kelly Criterion;
- confidence-weighted allocation.

Those capabilities belong to later implementation phases.

---

## Definition of Done

Phase 3 is complete when:

- Deployment Model interface exists;
- Equal Weight implementation passes;
- Fixed Budget implementation passes;
- identical Ranked Candidate Sets produce identical Capital Allocations;
- comprehensive unit tests pass;
- Python compilation passes;
- repository validation passes;
- worktree is clean.

---

# Phase 4 — Evaluator

## Objective

Implement deterministic historical outcome evaluation.

The Evaluator receives a Capital Allocation and computes the historical mining result using replayed historical outcomes.

The Evaluator is the sole authority responsible for translating deployment decisions into mining outcomes.

---

## Deliverables

Implement:

- Evaluator
- OutcomeResult
- Reward computation
- Dilution computation
- Capture efficiency computation
- Historical outcome attribution

The Evaluator shall consume only:

- historical replay;
- Capital Allocation.

---

## Responsibilities

### Evaluator

The Evaluator computes the historical outcome of every deployment decision.

Responsibilities include:

- determining whether a deployed square won;
- determining historical reward;
- determining dilution;
- determining solo vs shared wins;
- determining capture efficiency.

The Evaluator never:

- influences strategies;
- influences deployment;
- modifies replay;
- calculates aggregate metrics.

---

### OutcomeResult

Every evaluated deployment produces an immutable OutcomeResult.

OutcomeResult contains at minimum:

- round identifier;
- deployed square(s);
- winning square;
- hit or miss;
- ORE earned;
- SOL committed;
- number of miners sharing the reward;
- reward dilution;
- capture efficiency;
- optional evaluator metadata.

OutcomeResult becomes the sole input to the Metrics Engine.

---

## Historical Reward Computation

Historical rewards shall be computed exclusively from replayed historical outcomes.

Reward computation shall never:

- estimate future outcomes;
- simulate hypothetical competitors;
- use production state;
- use external market data.

Historical replay remains the only source of truth.

---

## Capture Efficiency

Capture Efficiency represents the fraction of the available reward captured by the deployment.

Capture Efficiency exists independently of:

- market valuation;
- ROI;
- portfolio optimization.

It is a mining-performance metric.

---

## Solo and Shared Wins

The Evaluator shall distinguish:

- solo wins;
- shared wins.

For shared wins, the Evaluator shall record:

- number of miners;
- reward dilution;
- resulting reward.

This information becomes part of the immutable experiment evidence.

---

## Architectural Principles

The Evaluator measures reality.

It never judges strategies.

It never compares experiments.

It simply answers:

> "Given this historical deployment, what would actually have happened?"

---

## Out of Scope

Phase 4 shall not implement:

- experiment aggregation;
- statistical analysis;
- report generation;
- experiment registry;
- portfolio optimization;
- market valuation.

Those responsibilities belong to later phases.

---

## Definition of Done

Phase 4 is complete when:

- historical reward computation is deterministic;
- solo and shared outcomes are reconstructed correctly;
- capture efficiency is computed correctly;
- immutable OutcomeResults are produced;
- comprehensive unit tests pass;
- Python compilation passes;
- repository validation passes;
- worktree is clean.

---

# Phase 5 — Metrics Engine and Experiment Registry

## Objective

Implement experiment aggregation, immutable experiment reporting, and deterministic experiment reconstruction.

This phase transforms historical OutcomeResults into immutable research artifacts.

The Metrics Engine is responsible for measuring experiments.

The Experiment Registry is responsible for preserving experiments.

Neither component influences replay, strategies, deployment, or evaluation.

---

## Deliverables

Implement:

- Metrics Engine
- Experiment Registry
- Experiment Report
- Experiment Identity
- Experiment Report persistence

---

## Responsibilities

### Metrics Engine

The Metrics Engine consumes immutable OutcomeResults.

It computes experiment-level performance.

The Metrics Engine never:

- modifies replay;
- modifies strategies;
- modifies deployment;
- modifies evaluation.

It only summarizes completed experiments.

---

### Primary Optimization Metrics

The Metrics Engine shall compute:

- Expected ORE mined
- Expected ORE per round
- Expected ORE per SOL committed
- Capture Efficiency
- Solo Win Frequency
- Shared Win Frequency
- Average Reward Dilution

These metrics represent mining performance.

---

### Secondary Metrics

The Metrics Engine shall compute:

- Hit Rate
- Miss Rate
- Square Selection Distribution
- Decision Entropy
- Crowd Avoidance Statistics

These metrics describe strategy behavior.

They are diagnostic rather than optimization targets.

---

### Operational Metrics

Every experiment shall permanently record:

- Runtime
- Replay Version
- Dataset Version
- Strategy Version
- Deployment Model Version
- Metrics Engine Version

---

## Experiment Registry

Every completed experiment shall receive an immutable identity.

Each experiment shall record:

- Experiment UUID
- Dataset Hash
- Replay Hash
- Strategy Hash
- Deployment Model Hash
- Metrics Engine Hash
- Configuration Hash
- Result Hash

The Experiment Registry exists solely to guarantee deterministic reproducibility.

Running an identical experiment again shall produce:

- a new Experiment UUID;
- identical deterministic results;
- identical configuration hashes.

---

## Experiment Reports

Experiment Reports are immutable.

Reports shall contain:

### Configuration

- Dataset
- Replay Version
- Strategy
- Deployment Model
- Experiment Configuration

### Results

- Primary Metrics
- Secondary Metrics
- Operational Metrics

### Provenance

- Experiment UUID
- All recorded hashes
- Timestamp
- Software versions

Experiment Reports shall never be modified after creation.

---

## Architectural Principles

Metrics describe completed experiments.

Reports preserve completed experiments.

Neither component influences historical replay.

Neither component influences future experiments.

The Experiment Registry is an immutable historical record.

---

## Out of Scope

Phase 5 shall not implement:

- machine learning;
- portfolio optimization;
- economic valuation;
- market ROI;
- live mining.

These capabilities belong to future RFCs.

---

## Definition of Done

Phase 5 is complete when:

- immutable Experiment Reports are produced;
- Experiment Registry identities are deterministic;
- all experiment hashes are recorded;
- historical experiments are reproducible;
- comprehensive unit tests pass;
- Python compilation passes;
- repository validation passes;
- worktree is clean.

---

# Phase 6 — Reference Strategies

## Objective

Provide deterministic baseline strategies for validating the Strategy Lab.

Reference strategies are intended for comparison and testing.

They are not expected to be competitive.

---

## Deliverables

Implement at minimum:

- Random
- Least Crowded
- Equal Distribution

Additional baseline strategies may be added later.

---

## Responsibilities

Reference strategies exist to:

- validate framework correctness;
- validate replay correctness;
- validate evaluator correctness;
- establish reproducible performance baselines.

---

## Definition of Done

Phase 6 is complete when:

- all reference strategies execute successfully;
- identical replay produces identical decisions;
- deterministic experiment reports are generated;
- baseline metrics are reproducible;
- repository validation passes.

---

# Implementation Completion Criteria

RFC-010 implementation is complete when:

- all six implementation phases are complete;
- all public interfaces are stable;
- all replay remains deterministic;
- all experiment artifacts are immutable;
- all experiments are reproducible;
- comprehensive automated tests pass;
- repository validation passes.

RFC-010 establishes the research platform upon which future Decision Engine, Portfolio Simulator, Paper Miner, and Live Miner capabilities shall be built.

No future implementation shall violate the architectural boundaries defined by RFC-010 without an explicit revision to the RFC itself.
