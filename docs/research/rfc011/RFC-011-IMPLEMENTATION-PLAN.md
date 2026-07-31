# RFC-011 Implementation Plan

**Status:** Approved and Frozen

This document defines the implementation sequencing for RFC-011.

RFC-011 defines the architecture.

This document defines the engineering plan.

It does not redefine architecture.

---

# Implementation Philosophy

Implementation shall proceed incrementally.

Each phase shall:

- preserve RFC-010 interfaces;
- preserve deterministic replay;
- preserve Research Domain isolation;
- remain independently testable;
- introduce no production reachability.

Every phase shall conclude with:

- implementation;
- validation;
- review;
- commit;
- push.

No later phase may be implemented early.

No placeholder implementations shall be introduced.

The phase dependency order is:

```text
Economic Scenario Foundation

↓

Allocation Materialization

↓

Pre-Transaction Protocol Constraints

↓

Transaction and Inclusion

↓

ORE Settlement

↓

Economic Simulation Runner

↓

Economic Metrics

↓

Economic Simulation Record

↓

CLI Integration
```

Each phase owns one architectural responsibility. A later phase consumes the
immutable outputs of earlier phases rather than reimplementing their behavior.

---

# Phase 1 — Economic Scenario Foundation

## Objective

Establish the immutable configuration and participant resource state required
for every economic simulation.

## Deliverables

Implement:

- EconomicScenario;
- ParticipantEconomicState;
- budget model;
- Scenario identity; and
- Scenario validation.

The Economic Scenario shall define:

- protocol revision;
- participant initial SOL balance;
- per-round deployment budget;
- capital reserve rules;
- lamport apportionment rule;
- fee assumptions;
- checkpoint assumptions;
- transaction assumptions;
- outcome policy;
- replay and dataset identities;
- deterministic component identities; and
- deterministic Scenario identity.

Participant Economic State shall define:

- available SOL in lamports;
- accrued ORE;
- accrued SOL;
- one 25-element deployed-lamports vector;
- occupied-square state derived from that vector;
- checkpoint state;
- cumulative protocol costs;
- cumulative transaction costs;
- current round identity; and
- last economically settled round.

SOL and ORE shall remain explicitly separate native balances.

No protocol behavior shall be implemented during this phase.

## Definition of Done

- Immutable scenario model.
- Immutable participant state.
- Explicit lamport-denominated budget and reserves.
- Deterministic identities.
- Validation complete.
- Unit tests complete.

---

# Phase 2 — Allocation Materialization

## Objective

Convert RFC-010 Deployment Decisions into exact protocol-denominated proposed
deployments.

## Deliverables

Implement:

- Allocation Materializer;
- budget-share interpretation;
- lamport materialization;
- deterministic rounding; and
- allocation amount/weight validation.

The materializer shall:

- consume DeploymentDecision;
- consume EconomicScenario;
- validate allocation amount and allocation weight consistency;
- validate that total allocation amount does not exceed one;
- preserve intentional undeployed budget;
- apply the configured deployable budget;
- apply the canonical apportionment rule;
- preserve deterministic candidate ordering; and
- produce one proposed 25-element lamport vector.

The materializer shall reject:

- non-finite or negative values;
- inconsistent amount and weight representations;
- total allocation above the configured budget share;
- duplicate or invalid square identities; and
- nondeterministic or unrepresentable lamport allocation.

No settlement shall occur.

No protocol constraints beyond allocation-shape validation shall be evaluated.

## Definition of Done

- Deterministic 25-element lamport vectors.
- Canonical integer rounding.
- Allocation amount/weight consistency enforced.
- Budget-share validation complete.
- Intentional undeployed capital preserved.
- Unit tests complete.

---

# Phase 3 — Pre-Transaction Protocol Constraint Model

## Objective

Validate every ORE protocol constraint knowable before transaction planning.

## Deliverables

Implement:

- ProtocolConstraintModel;
- pre-transaction feasibility validation;
- immutable constraint violations;
- ProtocolDeploymentPlan; and
- immutable protocol rejection.

The Protocol Constraint Model shall validate:

- exactly one 25-square deployment vector;
- square identifiers in the protocol domain;
- positive integer lamports for deployed squares;
- no duplicate square allocation;
- occupied-square restrictions;
- one positive deployment per authority-round-square;
- authority consistency;
- current-round consistency;
- checkpoint eligibility;
- protocol revision compatibility;
- participant available balance;
- required reserves; and
- deployment budget feasibility.

The Protocol Constraint Model shall either:

- produce an immutable ProtocolDeploymentPlan representing
  pre-transaction-feasible deployment; or
- produce an immutable rejection describing every failed pre-transaction
  constraint.

Phase 3 shall not evaluate:

- instruction packing;
- transaction grouping;
- transaction fees;
- compute assumptions;
- transaction size;
- deployment scheduling;
- inclusion timing;
- inclusion success; or
- transaction feasibility.

Those responsibilities belong exclusively to Phase 4.

No settlement shall occur.

No protocol-native rewards shall be calculated.

## Definition of Done

- Deterministic pre-transaction constraint validation.
- Allocation, square, occupied-square, checkpoint, authority, revision, and
  budget constraints fail closed.
- Immutable ProtocolDeploymentPlan.
- Immutable protocol rejection.
- No Phase 4 responsibility implemented.
- Unit tests complete.

---

# Phase 4 — Transaction and Inclusion Model

## Objective

Convert a pre-transaction-feasible ProtocolDeploymentPlan into deterministic
protocol actions and determine transaction feasibility and inclusion.

## Deliverables

Implement:

- TransactionModel;
- InclusionModel;
- instruction packing;
- transaction planning;
- transaction grouping;
- fee calculation;
- compute and size assumptions;
- deployment scheduling; and
- TransactionInclusionResult.

The Transaction Model shall consume:

- ProtocolDeploymentPlan; and
- EconomicScenario.

It shall determine:

- required ORE Deploy instructions;
- square mask and per-square amount for every instruction;
- deterministic instruction ordering;
- transaction grouping;
- transaction count;
- transaction and priority fees;
- compute assumptions;
- transaction-size assumptions;
- assumed submission slot;
- assumed inclusion slot;
- deployment scheduling;
- inclusion success or rejection; and
- complete transaction feasibility.

The TransactionInclusionResult shall preserve:

- transaction-plan identity;
- included or unincluded status;
- all modeled costs;
- all inclusion assumptions; and
- exact rejection reasons when inclusion or transaction feasibility fails.

The model shall remain entirely offline.

No RPC access.

No transaction construction or submission.

No network interaction.

No settlement shall occur.

## Definition of Done

- Deterministic instruction and transaction plans.
- Deterministic transaction grouping.
- Deterministic fee calculation.
- Compute and size assumptions validated.
- Deterministic scheduling and inclusion.
- Unincluded results fail closed with exact reasons.
- Unit tests complete.

---

# Phase 5 — ORE Settlement Engine

## Objective

Implement deterministic protocol-native settlement and one-round economic
result construction.

## Deliverables

Implement:

- ORESettlementModel;
- EconomicRoundResult;
- participant state transition calculation;
- SOL settlement;
- ORE settlement;
- protocol and transaction fee accounting;
- counterfactual aggregate adjustment;
- Evaluation Result reconciliation; and
- rejection and unincluded result construction.

For an included deployment, the Settlement Engine shall consume both:

- ProtocolDeploymentPlan; and
- TransactionInclusionResult.

It shall additionally consume:

- EvaluationResult;
- finalized replay facts;
- EconomicScenario; and
- ParticipantEconomicState.

For a rejected or unincluded deployment, it shall consume the immutable
rejection produced by Phase 3 or Phase 4 and produce an immutable rejected or
unincluded EconomicRoundResult without settlement.

The Settlement Engine shall:

- reconcile the finalized winning-square fact with EvaluationResult;
- reject any mismatch;
- insert the synthetic participant deployment at the modeled inclusion point;
- adjust applicable historical aggregate deployment deterministically;
- prevent double-counting a historical participant position;
- preserve historical entropy and winning square;
- calculate deployed SOL;
- calculate returned principal and SOL winnings;
- calculate protocol deductions;
- account for transaction and priority fees;
- account for checkpoint costs;
- calculate ORE earned;
- calculate split or solo reward treatment;
- calculate dilution;
- calculate capture efficiency;
- calculate the resulting ParticipantEconomicState; and
- preserve outcome provenance in EconomicRoundResult.

All settlement shall use deterministic integer arithmetic.

SOL and ORE shall remain separate native denominations in every result and
state transition.

No market valuation shall occur.

No SOL/ORE conversion shall occur.

## Definition of Done

- Deterministic included-deployment settlement.
- Immutable settled EconomicRoundResult.
- Immutable rejected EconomicRoundResult.
- Immutable unincluded EconomicRoundResult.
- Evaluation Result reconciliation fails closed.
- Counterfactual aggregates are adjusted without historical double-counting.
- Outcome provenance is preserved.
- SOL and ORE remain explicitly separate.
- Deterministic participant state transition calculation.
- Unit tests complete.

---

# Phase 6 — Economic Simulation Runner

## Objective

Orchestrate RFC-011 sequentially across ordered RFC-010 replay results without
moving orchestration into the CLI.

## Deliverables

Implement:

- EconomicSimulationRunner;
- ordered replay execution;
- sequential ParticipantEconomicState transitions;
- checkpoint continuity;
- missing-outcome handling;
- outcome-complete interval handling; and
- ordered EconomicRoundResult production.

The Economic Simulation Runner shall consume:

- one immutable RFC-010 experiment;
- its ordered DeploymentDecisions and EvaluationResults;
- immutable replay facts;
- one EconomicScenario; and
- one initial ParticipantEconomicState.

For every replay round, it shall invoke the existing RFC-011 components in
order:

```text
Allocation Materializer

↓

Protocol Constraint Model

↓

Transaction and Inclusion Model

↓

ORE Settlement Model
```

The Runner shall:

- preserve RFC-010 replay ordering;
- preserve one ordered EconomicRoundResult for every processed round;
- apply a state transition only after a deterministically settled result;
- preserve checkpoint continuity;
- fail closed when participant state continuity is broken;
- classify missing finalized outcomes without fabrication;
- preserve observed or enriched outcome provenance;
- prevent an unresolved round from silently advancing participant state;
- simulate only contiguous outcome-complete intervals;
- require explicit immutable initial state for each independently simulated
  interval;
- preserve protocol and component identities; and
- produce the ordered EconomicRoundResult sequence consumed by later phases.

The Runner shall not:

- calculate aggregate metrics;
- construct the final EconomicSimulationRecord;
- modify RFC-010 artifacts;
- skip an unresolved state transition and continue with an invented balance;
- access RPC or production state; or
- implement CLI behavior.

## Definition of Done

- Deterministic ordered execution.
- Sequential participant state transitions.
- Checkpoint continuity enforced.
- Missing outcomes fail closed.
- Contiguous outcome-complete interval behavior validated.
- Ordered EconomicRoundResults produced.
- Outcome provenance preserved.
- End-to-end component orchestration tests complete.

---

# Phase 7 — Economic Metrics

## Objective

Aggregate ordered EconomicRoundResults into deterministic protocol-native
Economic Experiment Metrics.

## Deliverables

Implement:

- EconomicMetricsEngine; and
- EconomicExperimentMetrics.

The Economic Metrics Engine shall consume only the ordered
EconomicRoundResults produced by the Economic Simulation Runner.

It shall aggregate:

- economically processed rounds;
- settled rounds;
- rejected rounds;
- unincluded rounds;
- missing-outcome rounds;
- total and mean deployed lamports;
- returned principal and SOL winnings;
- protocol fees;
- transaction and priority fees;
- checkpoint costs;
- gross SOL outflow;
- gross SOL inflow;
- net SOL change;
- deployment-budget utilization;
- maximum concurrent SOL exposure;
- ORE earned;
- mean ORE per settled round;
- ORE per SOL deployed;
- solo reward frequency;
- split reward frequency;
- winning-square capital share;
- dilution;
- capture efficiency;
- net SOL return rate; and
- completeness by outcome provenance.

Native-unit return metrics shall preserve explicit separation:

- SOL-denominated return uses only SOL flows.
- ORE yield per SOL committed preserves both units.

The Metrics Engine shall not:

- rank strategies;
- optimize deployments;
- recompute settlement;
- change ParticipantEconomicState;
- convert ORE to SOL;
- combine SOL and ORE into one ROI;
- convert either asset to fiat; or
- construct the EconomicSimulationRecord.

## Definition of Done

- Deterministic EconomicExperimentMetrics.
- Native-unit return metrics complete.
- SOL and ORE remain separate.
- Completeness and provenance aggregation complete.
- No simulation-record responsibility implemented.
- Unit tests complete.

---

# Phase 8 — Economic Simulation Record

## Objective

Construct the immutable, reproducible record for one completed economic
simulation.

## Deliverables

Implement:

- EconomicSimulationRecord;
- deterministic record identity;
- deterministic result hashing; and
- record validation.

The Economic Simulation Record shall consume, not compute:

- EconomicExperimentMetrics from Phase 7;
- ordered EconomicRoundResults from Phase 6;
- EconomicScenario;
- initial ParticipantEconomicState;
- terminal ParticipantEconomicState; and
- RFC-010 experiment and replay identities.

It shall preserve:

- RFC-010 experiment identity;
- Economic Scenario identity and hash;
- protocol revision;
- dataset identity;
- replay identity;
- Allocation Materializer identity;
- Protocol Constraint Model identity;
- Transaction and Inclusion Model identities;
- ORE Settlement Model identity;
- Economic Simulation Runner identity;
- Economic Metrics Engine identity;
- initial participant state hash;
- terminal participant state hash;
- ordered EconomicRoundResult identities;
- EconomicExperimentMetrics;
- completeness metadata;
- outcome-provenance summary; and
- deterministic result hash.

The Simulation Record shall never:

- recompute metrics;
- recompute settlement;
- reorder EconomicRoundResults;
- hide rejected, unincluded, or missing-outcome results; or
- contain mutable runtime state.

## Definition of Done

- Immutable EconomicSimulationRecord.
- Deterministic component identities complete.
- Ordered EconomicRoundResult identities preserved.
- Completeness metadata preserved.
- Deterministic record and result hashes.
- Record validation complete.
- Unit tests complete.

---

# Phase 9 — CLI Integration

## Objective

Expose RFC-011 through the Strategy Lab command-line interface without placing
economic orchestration in the CLI.

## Deliverables

Extend:

```text
python -m orev3.strategy_lab.run
```

to support economic simulation.

The CLI shall invoke EconomicSimulationRunner.

It shall not directly orchestrate:

- allocation materialization;
- protocol constraints;
- transaction planning;
- settlement;
- participant state transitions; or
- checkpoint continuity.

The CLI shall allow selection of:

- Economic Scenario;
- deployment budget;
- protocol revision; and
- output location.

Any CLI-supplied scenario value shall participate in deterministic Economic
Scenario construction and identity. It shall not mutate an existing scenario
after validation.

Experiment summaries shall include:

Dataset:

- replay readiness;
- completeness;
- evaluated rounds.

Decision:

- strategy;
- deployment model.

Economics:

- settled, rejected, unincluded, and missing-outcome rounds;
- deployed SOL;
- returned SOL;
- net SOL change;
- ORE earned;
- fees;
- capture efficiency;
- completeness;
- participant ending SOL balance; and
- participant ending ORE balance.

Validation:

- deterministic replay;
- deterministic economics;
- deterministic component identities; and
- deterministic record generation.

## Definition of Done

- CLI delegates orchestration to EconomicSimulationRunner.
- End-to-end execution.
- Integration tests complete.
- Research Domain validation complete.

---

# Implementation Coverage Matrix

| RFC-011 responsibility | Owning phase |
|---|---:|
| Economic Scenario and participant resource state | 1 |
| Allocation amount/weight consistency and lamport materialization | 2 |
| Pre-transaction protocol feasibility | 3 |
| Instruction packing, transaction feasibility, fees, scheduling, and inclusion | 4 |
| Evaluation reconciliation, counterfactual settlement, and one-round results | 5 |
| Ordered execution, checkpoint continuity, missing outcomes, and interval handling | 6 |
| Economic aggregation and native-unit return metrics | 7 |
| Immutable simulation record, identities, and completeness metadata | 8 |
| User interface only | 9 |

No responsibility is intentionally duplicated across phases.

Where one concept crosses phases, its role is distinct:

- Phase 1 validates budget configuration.
- Phase 2 validates allocation shares against the configured budget.
- Phase 3 validates participant balance and reserve feasibility.
- Phase 1 defines fee assumptions.
- Phase 4 calculates modeled transaction fees.
- Phase 5 accounts for those fees in one-round settlement.
- Phase 6 preserves those results in replay order.
- Phase 7 aggregates them.
- Phase 8 records the aggregate and its ordered evidence.

---

# Implementation Completion Criteria

RFC-011 implementation is complete when:

- every implementation phase has passed review;
- every phase has been validated independently;
- every responsibility in the coverage matrix is implemented exactly once;
- deterministic replay is preserved;
- RFC-010 interfaces remain unchanged;
- protocol-native economic simulation is reproducible;
- rejected and unincluded deployments fail closed;
- Evaluation Result reconciliation passes;
- counterfactual adjustment and double-count prevention pass;
- missing outcomes cannot silently advance participant state;
- contiguous outcome-complete intervals are reproducible;
- SOL and ORE remain separate native denominations;
- immutable Economic Simulation Records are generated;
- ordered EconomicRoundResult identities and completeness metadata are
  preserved;
- all Research Domain tests pass; and
- repository validation passes under Repository Architecture governance.

Implementation shall conclude with:

- implementation complete;
- validation complete;
- documentation complete;
- commit; and
- push.
