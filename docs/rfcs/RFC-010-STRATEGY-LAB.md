# RFC-010 — Deterministic Strategy Laboratory

**Status:** Draft for Human Review  
**Scope:** Offline Research and Experimentation Architecture

---

# 1. Purpose

The Deterministic Strategy Laboratory ("Strategy Lab") is the offline experimentation framework for ORE Miner V3.

Its purpose is to evaluate mining strategies against historical replay data in a deterministic, reproducible, and market-agnostic environment.

The Strategy Lab exists to answer one question:

> **Given only the information available before each historical mining round began, which sequence of decisions would have produced the best mining performance?**

The Strategy Lab never:

- performs live mining;
- submits transactions;
- modifies production state;
- modifies authoritative ledgers;
- interacts with production governance.

Its primary optimization objective is **expected mining performance**.

Mining performance is intentionally independent of:

- market valuation;
- USD-denominated ROI;
- portfolio optimization;
- capital management.

Those analyses belong to later system components.

The Strategy Lab evaluates decision quality independently from capital allocation and economic valuation.

---

# 2. Goals

The Strategy Lab shall:

- Evaluate mining strategies deterministically.
- Evaluate strategies exclusively against historical replay data.
- Prevent future-information leakage.
- Separate decision quality from capital allocation.
- Produce immutable experiment reports.
- Produce reproducible experiment results.
- Support simple heuristic strategies.
- Support sophisticated adaptive strategies.
- Support multiple deployment models evaluating the same strategy independently.
- Provide the research foundation for future Decision Engine, Portfolio Simulator, Paper Miner, and Live Miner components.

---

# 3. Non-Goals

RFC-010 does **not** define:

- Live mining.
- Transaction submission.
- Wallet management.
- Production governance.
- Production recovery.
- Economic portfolio optimization.
- USD-denominated ROI.
- Market forecasting.
- Machine learning algorithms.
- Reinforcement learning.
- Bayesian optimization.
- Neural-network architectures.

Those capabilities are intentionally reserved for future RFCs.

---

# 4. Design Principles

The Strategy Lab is governed by the following architectural principles.

## 4.1 Deterministic

Given:

- the same replay dataset;
- the same replay engine;
- the same strategy;
- the same deployment model;
- the same experiment configuration;

the Strategy Lab shall produce identical results.

No experiment outcome may depend upon execution order, wall-clock time, machine state, network availability, or any other non-deterministic influence.

---

## 4.2 Replay First

Every experiment executes entirely against historical replay data.

The Strategy Lab shall never interact with:

- live network state;
- production ledgers;
- production authorization;
- production governance;
- wallets;
- transactions.

Historical replay is the sole source of truth.

---

## 4.3 Separation of Concerns

The Strategy Lab separates mining research into independent responsibilities.

The Replay Engine reconstructs historical state.

The Strategy expresses preference.

The Deployment Model expresses conviction.

The Evaluator computes historical outcomes.

The Metrics Engine measures experiment performance.

Each component owns exactly one responsibility.

---

## 4.4 Market Agnostic

The Strategy Lab evaluates mining performance.

It intentionally does not evaluate:

- market profitability;
- USD-denominated return;
- token valuation;
- portfolio optimization.

Those analyses belong to later system components.

---

## 4.5 Immutable Experiments

Every completed experiment is immutable.

Experiment reports are never modified after creation.

Re-running an identical experiment creates a new immutable experiment with a new identity, even when every result is identical.

---

## 4.6 Versioned Components

Every experiment shall permanently record:

- replay version;
- dataset version;
- strategy version;
- deployment model version;
- metrics engine version.

Historical experiment results must remain reproducible after future software evolution.

---

## 4.7 Pure Strategies

Strategies express preference only.

Strategies never:

- allocate capital;
- evaluate themselves;
- access persistence;
- communicate with external systems;
- modify replay state.

Their sole responsibility is ranking historical opportunities.

---

## 4.8 No Future Information

Strategies may observe only information that would have been available immediately before the historical decision.

No future round, outcome, or replay artifact may influence strategy decisions.

Adaptive strategies may update internal state only after the evaluator reveals the completed historical outcome of the current round.

---

## 4.9 Strategy Explainability

Strategies may emit deterministic structured explanations describing why candidates were ranked.

These explanations are immutable experiment artifacts.

The Strategy Lab preserves them exactly as produced.

It does not interpret, validate, or modify them.

Explainability exists to support:

- experiment review;
- debugging;
- visualization;
- strategy comparison;
- future research.

Structured explanations must remain deterministic under identical replay conditions.

---

# 5. System Architecture

The Strategy Lab is composed of independent components connected through immutable interfaces.

```
Historical Dataset
        │
        ▼
Replay Engine
        │
        ▼
Decision Context
        │
        ▼
Strategy
        │
        ▼
Ranked Candidate Set
        │
        ▼
Deployment Model
        │
        ▼
Capital Allocation
        │
        ▼
Evaluator
        │
        ▼
Metrics Engine
        │
        ▼
Experiment Report
```

Each component owns exactly one responsibility.

Components communicate only through explicitly defined interfaces.

No component may bypass another component's interface.

---

# 6. Component Responsibilities

## 6.1 Historical Dataset

The Historical Dataset is the immutable source of replay data.

Responsibilities:

- Store historical observations.
- Store historical outcomes.
- Preserve chronological ordering.
- Preserve experiment reproducibility.

The Historical Dataset is read-only during experimentation.

No experiment may modify historical replay data.

---

## 6.2 Replay Engine

The Replay Engine reconstructs historical mining state.

Responsibilities:

- Replay historical rounds.
- Reconstruct historical board state.
- Reconstruct historical treasury state.
- Reconstruct historical participant state.
- Produce deterministic Decision Context objects.

The Replay Engine is responsible only for reconstruction.

It never:

- evaluates strategies;
- allocates capital;
- computes rewards;
- measures performance.

---

## 6.3 Decision Context

Decision Context is the immutable view of historical information available immediately before a decision.

Decision Context intentionally exposes only information that would have been historically observable.

It must never expose:

- future rounds;
- future winners;
- future treasury values;
- replay implementation details.

Decision Context exists solely to support fair strategy evaluation.

---

## 6.4 Strategy

A Strategy expresses preference.

Input:

Decision Context.

Output:

Ranked Candidate Set.

A Strategy never:

- allocates capital;
- computes rewards;
- evaluates itself;
- accesses persistence;
- accesses replay internals;
- communicates externally.

Strategies may maintain deterministic internal state across replayed rounds.

Internal state may evolve only after the Evaluator reveals the completed historical outcome of the current round.

Strategies must produce identical behavior when replaying identical historical data.

---

## 6.5 Ranked Candidate Set

A Ranked Candidate Set represents the strategy's ordered preferences.

Each candidate contains:

- square identifier;
- relative preference score;
- optional structured explanation.

Preference scores represent ordering only.

They are not probabilities.

They are not capital allocations.

They are not expected rewards.

The structured explanation is owned entirely by the strategy.

It may contain any deterministic metadata that explains why the strategy preferred that candidate.

Examples include:

- feature values;
- heuristic contributions;
- model confidence;
- historical observations;
- intermediate calculations.

The Strategy Lab stores structured explanations as immutable experiment artifacts.

It does not interpret, validate, or evaluate their contents.

Deployment Models determine how strategy preferences influence capital allocation.

Deployment Models must ignore strategy explanations unless explicitly designed to consume them.

---

# 7. Deployment Model

The Deployment Model is responsible solely for expressing conviction.

It converts a Ranked Candidate Set into a Capital Allocation.

Strategies never allocate capital.

Deployment Models never modify strategy preferences.

This separation allows identical strategies to be evaluated under multiple deployment policies.

Example deployment models include:

- Equal Weight
- Fixed Budget
- Confidence Weighted
- Kelly Criterion
- Portfolio Aware

RFC-010 defines only the Deployment Model interface.

Future RFCs define specific deployment algorithms.

---

# 8. Capital Allocation

Capital Allocation represents the deployment model's allocation decision.

Each allocation contains:

- selected square;
- allocation amount;
- allocation weight;
- deployment metadata.

Capital Allocation is the only object consumed by the Evaluator.

Strategies never directly influence allocation after producing their Ranked Candidate Set.

---

# 9. Evaluator

The Evaluator replays historical outcomes.

Given:

- historical replay;
- Capital Allocation;

it computes:

- hit;
- miss;
- ORE earned;
- SOL committed;
- solo win;
- shared win;
- dilution;
- capture efficiency.

The Evaluator is responsible only for historical outcome computation.

It never:

- modifies replay state;
- modifies strategy state;
- influences future decisions.

---

# 10. Metrics Engine

The Metrics Engine aggregates experiment performance.

## Primary Optimization Metrics

These metrics represent the primary optimization targets of the Strategy Lab.

- Expected ORE mined
- Expected ORE per round
- Expected ORE per SOL committed
- Capture Efficiency
- Solo win frequency
- Shared win frequency
- Average dilution

## Secondary Metrics

These metrics describe decision quality and strategy characteristics.

- Hit rate
- Miss rate
- Square selection distribution
- Decision entropy
- Crowd avoidance

These metrics are diagnostic only.

## Operational Metrics

Every experiment records:

- Runtime
- Replay version
- Dataset version
- Strategy version
- Deployment Model version
- Metrics Engine version

The Metrics Engine summarizes experiments only.

It never influences strategy behavior.

---

# 11. Experiment Registry

Every experiment produces an immutable Experiment Report.

Each experiment receives:

- Experiment UUID
- Dataset hash
- Replay hash
- Strategy hash
- Deployment Model hash
- Metrics Engine hash
- Configuration hash
- Result hash

Experiment reports are immutable.

Running the same experiment again creates a new experiment with a new UUID while producing identical deterministic results.

---

# 12. Strategy Lifecycle

Strategies may be stateful.

Lifecycle:

```
initialize()

↓

choose()

↓

evaluate()

↓

update()

↓

repeat
```

State may evolve only after the Evaluator reveals the completed historical outcome of the current round.

No future information may influence state.

Replaying identical historical data must produce identical strategy state evolution.

---

# 13. Invariants

The Strategy Lab shall preserve:

- deterministic replay;
- immutable experiments;
- reproducible results;
- versioned datasets;
- market independence;
- separation of strategy and deployment;
- separation of deployment and evaluation;
- no future-information leakage;
- identical replay producing identical results;
- exactly one strategy per experiment;
- exactly one deployment model per experiment;
- exactly one evaluator per experiment.

---

# 14. Out of Scope

RFC-010 intentionally does not define:

- machine learning;
- reinforcement learning;
- Bayesian optimization;
- neural networks;
- portfolio optimization;
- live mining;
- economic valuation;
- market ROI.

These capabilities belong to future RFCs.

---

# 15. Success Criteria

RFC-010 is complete when a user can execute a deterministic historical experiment by selecting:

- one replay dataset;
- one strategy;
- one deployment model;

and produce an immutable Experiment Report.

The resulting experiment shall be reproducible from its recorded configuration and versioned artifacts.

Future Strategy Lab capabilities shall extend this architecture without modifying its core responsibilities or interfaces.
