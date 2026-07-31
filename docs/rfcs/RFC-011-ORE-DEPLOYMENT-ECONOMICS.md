# RFC-011 — ORE Deployment Economics

**Status:** Approved and Frozen
**Scope:** Offline, protocol-faithful economic simulation in the Research Domain

---

# 1. Purpose

RFC-011 defines the architectural layer that converts RFC-010 Strategy Lab
deployment decisions into protocol-faithful ORE economic simulations.

RFC-010 answers:

> Which squares did a strategy prefer, and how did a Deployment Model express
> conviction across them?

RFC-011 answers:

> Given an explicit participant budget and an immutable ORE protocol model,
> what feasible on-chain deployment would that abstract decision represent,
> and what protocol-native economic result would it have produced?

RFC-011 extends RFC-010. It does not replace or redesign:

- Replay;
- Decision Context;
- Strategy;
- Ranked Candidate Set;
- Deployment Model;
- Deployment Decision;
- Evaluator;
- Evaluation Result;
- Metrics Engine; or
- Experiment Registry.

Economics consumes their immutable outputs through a separate downstream
boundary.

RFC-011 belongs entirely to the Research Domain defined by
[Repository Architecture](../architecture/REPOSITORY-ARCHITECTURE.md).
It produces research evidence. It creates no operational authority and has no
production reachability.

---

# 2. Motivation

RFC-010 intentionally separates strategy preference from capital management
and market valuation. Its built-in Deployment Models currently express
conviction using an abstract unit allocation:

- Equal Weight divides one abstract unit among all candidates.
- Top Ranked assigns one abstract unit to the first candidate.

The existing Evaluator records a hit when the historical winning square has a
positive allocation. It does not interpret:

- the magnitude of that allocation;
- the SOL required to deploy it;
- transaction or checkpoint costs;
- protocol settlement;
- reward dilution; or
- capital efficiency.

This behavior is internally correct and documented in the
[Deployment Semantics Investigation](../research/deployment-semantics-investigation.md).
It also means a deployment covering all 25 squares can produce a 100% hit rate
without expressing the economic cost of that coverage.

The [ORE Resource Semantics Investigation](../research/ore-resource-semantics.md)
establishes that the protocol's primary participant-controlled resource is
SOL-denominated capital exposure over a 25-square, authority-specific
deployment vector. Square capacity, round timing, transaction fees, compute,
and transaction inclusion constrain that exposure. “Number of miners” is an
authority-count statistic, not a unit of participant capital.

RFC-011 introduces the missing economic interpretation while preserving every
RFC-010 responsibility and interface.

---

# 3. Goals

RFC-011 shall:

- Preserve the RFC-010 execution pipeline unchanged.
- Convert an immutable Deployment Decision into an exact lamport deployment.
- Represent a participant's simulated SOL budget explicitly.
- Enforce the ORE protocol constraints relevant to a simulated deployment.
- Model deterministic transaction inclusion assumptions.
- Reconstruct protocol-native SOL and ORE settlement.
- Measure deployment cost, dilution, reward, and capital efficiency.
- Keep ORE and SOL as separate native denominations.
- Preserve outcome provenance and replay completeness boundaries.
- Produce deterministic, immutable economic results.
- Support reproducible comparison of the same RFC-010 experiment under
  different economic scenarios.
- Remain offline and independent from production systems.

---

# 4. Non-Goals

RFC-011 does not define:

- a new Strategy interface;
- a new Deployment Model interface;
- a replacement Evaluator;
- live mining;
- wallet access or wallet management;
- private keys or signers;
- transaction construction, signing, or submission;
- RPC access during an experiment;
- production collection;
- RFC-008 or RFC-009 governance;
- market prices;
- USD-denominated valuation;
- combined SOL-and-ORE profit;
- portfolio optimization;
- automatic strategy selection;
- adaptive budget optimization;
- multi-wallet identity attribution;
- prediction of network congestion;
- dataset repair or outcome enrichment;
- claims, token sales, swaps, or treasury management;
- tax or accounting treatment.

Those concepts remain outside RFC-011.

---

# 5. Architectural Position

RFC-010 remains the authoritative architecture for Strategy Lab execution.

The preserved pipeline is:

```text
Replay

↓

Strategy

↓

Deployment

↓

Evaluation
```

RFC-011 consumes the immutable artifacts produced by that pipeline:

```text
RFC-010 Replay Facts ──────────────────────────────┐
                                                   │
RFC-010 Deployment Decision ──────────────────────┼──▶ ORE Economics
                                                   │
RFC-010 Evaluation Result ────────────────────────┘

Immutable Economic Scenario ─────────────────────────▶ ORE Economics

ORE Economics

↓

Economic Round Result

↓

Economic Experiment Metrics

↓

Immutable Economic Simulation Record
```

The RFC-010 Evaluator still determines the factual hit or miss for the
Deployment Decision. RFC-011 does not reinterpret or replace that result.

The economics layer uses the same finalized historical outcome to calculate
the protocol-native consequence of the materialized deployment. A decision
may therefore be:

- an RFC-010 hit with very low capital efficiency;
- an RFC-010 miss with a protocol-native capital loss;
- infeasible under its economic scenario; or
- economically unevaluable because the finalized outcome is unavailable.

These are separate facts.

---

# 6. Allocation Semantics

## 6.1 RFC-010 semantics remain unchanged

Outside RFC-011, `allocation_amount` remains the abstract, deterministic
allocation magnitude emitted by a Deployment Model.

It is not inherently:

- lamports;
- SOL;
- a transaction count;
- a miner count;
- a probability;
- an expected reward; or
- a wallet balance.

RFC-011 does not change the stored RFC-010 object or require a Strategy to know
about capital.

## 6.2 RFC-011 economic interpretation

For an RFC-011-compatible Deployment Decision, `allocation_amount` is
interpreted as a **dimensionless share of the participant's configured
per-round deployment budget**.

The interpretation is:

```text
square budget share = allocation_amount

square lamports = configured deployable budget × square budget share
```

The sum of all `allocation_amount` values in one economically materialized
decision must be between zero and one, inclusive.

- A sum of `1` deploys the full configured budget.
- A sum below `1` leaves the remainder undeployed.
- A sum of `0` produces no deployment.
- A sum above `1` is economically infeasible and fails closed.

This interpretation preserves the existing built-in Deployment Models:

- Top Ranked assigns 100% of the budget to one square.
- Equal Weight assigns equal budget shares whose total is 100%.

## 6.3 Allocation weight

`allocation_weight` remains a dimensionless statement of relative conviction
among deployed candidates.

For an economically compatible decision:

- every positive `allocation_amount` must have a positive
  `allocation_weight`;
- zero-amount allocations must not create protocol deployment;
- weights must be consistent with the relative distribution of committed
  budget; and
- inconsistent amount and weight representations fail closed.

`allocation_weight` is not multiplied by capital independently. It cannot
cause a second allocation.

## 6.4 Canonical monetary unit

Every RFC-011 monetary value is represented canonically in **lamports**.

SOL is a presentation unit only:

```text
1 SOL = 1,000,000,000 lamports
```

Lamports are required because:

- the ORE program accepts integer lamport amounts;
- Solana fees are paid in lamports;
- integer arithmetic is deterministic;
- float-denominated SOL would introduce rounding ambiguity; and
- protocol settlement uses integer arithmetic.

RFC-011 never stores a floating-point SOL amount as economic authority.

## 6.5 Deterministic materialization

Budget shares may not divide an integer lamport budget evenly.

The Economic Scenario must therefore identify one canonical, versioned
apportionment and rounding rule. That rule must:

- produce nonnegative integer lamports;
- never allocate more than the configured deployment budget;
- preserve deterministic candidate ordering;
- resolve equal remainders deterministically;
- preserve an intentional undeployed remainder; and
- be included in the economic configuration identity.

No implementation may choose rounding based on machine behavior, map order,
or wall-clock state.

---

# 7. Participant Resource Model

## 7.1 Protocol participant

RFC-011 models one ORE protocol authority.

This is the narrow identity that the ORE program itself recognizes through one
authority-derived Miner account. It is not a claim about a natural person.

Multi-authority or multi-wallet coordination is outside RFC-011.

## 7.2 Participant Economic State

The participant's simulated economic state contains:

- available SOL balance in lamports;
- configured maximum deployment budget per round in lamports;
- reserved transaction and checkpoint costs;
- current round identifier;
- one 25-element deployed-lamports vector;
- occupied-square state derived from that vector;
- prior-round checkpoint status;
- accrued claimable SOL;
- accrued claimable ORE;
- cumulative protocol fees;
- cumulative transaction fees; and
- the last economically settled round.

Participant Economic State is separate from Strategy state.

It is:

- initialized only by the Economic Scenario;
- advanced only by protocol-economic events;
- never visible to Strategy;
- never written into Decision Context;
- deterministic under identical inputs; and
- immutable in every emitted result, even when an implementation uses an
  internal state transition mechanism.

## 7.3 Deployment budget

The per-round deployment budget is an immutable scenario parameter expressed
in lamports.

The deployable amount for a round is bounded by:

- the configured per-round maximum;
- the participant's available SOL;
- mandatory reserves for deterministically modeled costs; and
- any capital still unavailable because a prior protocol transition has not
  settled.

The economics layer never invents additional capital.

No external deposit, withdrawal, ORE sale, SOL purchase, or capital injection
occurs during one economic simulation.

## 7.4 Separate native balances

SOL and ORE remain separate balances.

RFC-011 may calculate:

- SOL deployed;
- SOL returned;
- SOL fees;
- net SOL change;
- ORE earned; and
- ORE earned per unit of SOL deployed.

RFC-011 shall not add SOL and ORE together or convert one into the other.

---

# 8. Economic Scenario

Every simulation is governed by one immutable Economic Scenario.

The Economic Scenario records:

- scenario identifier and schema version;
- ORE program and protocol revision;
- participant initial SOL balance;
- per-round deployment budget;
- capital reserve rules;
- lamport apportionment rule;
- fee model;
- checkpoint model;
- transaction packing model;
- deterministic transaction-inclusion model;
- deployment timing rule;
- settlement model;
- replay and dataset identities;
- outcome-provenance policy;
- missing-outcome policy; and
- all component identities required for reproduction.

The scenario distinguishes three kinds of inputs:

## 8.1 Protocol facts

Protocol facts are behavior fixed by the selected ORE program revision.

Examples include:

- 25 squares;
- authority-specific Miner state;
- one positive recorded amount per authority–round–square;
- current-round validation;
- active-slot validation;
- prior-round checkpoint requirement;
- per-square deploy semantics;
- settlement arithmetic;
- protocol deductions; and
- checkpoint reserve behavior.

## 8.2 Historical facts

Historical facts come from immutable replay data.

Examples include:

- pre-decision board state;
- pre-decision round state;
- decision slot and slots remaining;
- aggregate per-square deployments at decision time;
- finalized entropy and winning square;
- finalized aggregate deployment;
- reward configuration;
- finalization state; and
- outcome provenance.

Historical outcomes are available only after the RFC-010 decision and
evaluation boundary.

## 8.3 Simulation assumptions

Simulation assumptions are deterministic, versioned choices required when
historical evidence does not contain a participant's counterfactual
transaction.

Examples include:

- transaction fee schedule;
- priority fee;
- instruction packing;
- inclusion latency;
- checkpoint transaction timing; and
- treatment of a transaction that would land after the round deadline.

Simulation assumptions must never be presented as observed historical facts.

---

# 9. Economics Components

## 9.1 Allocation Materializer

The Allocation Materializer consumes:

- the RFC-010 Deployment Decision;
- the participant's deployable round budget;
- the Economic Scenario; and
- protocol square-domain information.

It produces one exact 25-element proposed deployment vector in lamports.

It is responsible for:

- validating economic compatibility of allocation amounts and weights;
- applying the configured budget;
- applying canonical lamport rounding;
- preserving square identity;
- preserving undeployed capital; and
- rejecting over-allocation or malformed decisions.

It never:

- changes candidate rank;
- asks Strategy for another decision;
- evaluates an outcome;
- accesses future replay data; or
- selects a square not present in the Deployment Decision.

## 9.2 Protocol Constraint Model

The Protocol Constraint Model determines whether and how the proposed vector
can be expressed under the selected ORE protocol revision.

It validates:

- exactly 25 square positions;
- square identifiers in the protocol domain;
- no duplicate square allocation;
- positive integer lamports for deployed squares;
- occupied-square restrictions;
- authority and round consistency;
- prior-round checkpoint status;
- available balance and cost reserves;
- valid deployment timing;
- transaction packing feasibility;
- transaction size and compute assumptions; and
- deterministic inclusion before the round closes.

It produces either:

- an immutable feasible Protocol Deployment Plan; or
- an immutable rejection with exact failed constraints.

It does not silently:

- scale down capital;
- drop squares;
- change allocation rank;
- move a deployment to another round;
- assume successful inclusion; or
- repair participant state.

## 9.3 Transaction and Inclusion Model

The Transaction and Inclusion Model converts the feasible 25-square vector
into a deterministic protocol action plan.

The ORE Deploy instruction applies one amount to every square selected in its
mask. Therefore, squares with different lamport amounts may require separate
Deploy instructions. The transaction model must account for this protocol
shape rather than treating an arbitrary vector as one unconstrained action.

The model records:

- Deploy instructions required;
- squares and per-square amount in each instruction;
- transaction grouping;
- transaction fees;
- compute and size feasibility;
- assumed submission slot;
- assumed inclusion slot; and
- included or rejected status.

The model is deterministic and offline. It does not call RPC, estimate live
congestion, or submit a transaction.

## 9.4 ORE Settlement Model

The ORE Settlement Model consumes:

- the included Protocol Deployment Plan;
- the finalized replay outcome;
- the RFC-010 Evaluation Result;
- the relevant historical round state;
- the selected ORE protocol revision; and
- the participant's pre-settlement economic state.

It calculates the participant's protocol-native settlement using the selected
program revision's integer arithmetic.

It is responsible for:

- deployed SOL by square;
- winning-square deployment;
- principal returned;
- SOL winnings;
- protocol deductions;
- ORE reward;
- split or solo reward treatment;
- dilution;
- capture share;
- checkpoint cost and state;
- post-round SOL and ORE balances; and
- the participant state transition.

The Settlement Model must reconcile its winning-square fact with the RFC-010
Evaluation Result. A mismatch fails closed.

It never modifies the historical replay record.

## 9.5 Economic Metrics Engine

The Economic Metrics Engine consumes immutable Economic Round Results.

It calculates experiment-level protocol-native metrics only.

It never:

- influences replay;
- changes a Strategy;
- changes a Deployment Model;
- changes Participant Economic State;
- values ORE in SOL or fiat; or
- selects a preferred experiment.

## 9.6 Economic Simulation Record

Every completed economics run produces an immutable Economic Simulation
Record linked to exactly one RFC-010 experiment.

The record contains:

- RFC-010 experiment identity;
- Economic Scenario identity and hash;
- protocol revision;
- dataset and replay identities;
- materialization-rule identity;
- constraint-model identity;
- transaction-model identity;
- settlement-model identity;
- economic-metrics identity;
- initial participant state hash;
- terminal participant state hash;
- ordered Economic Round Result identities;
- Economic Experiment Metrics;
- completeness and provenance summary; and
- deterministic result hash.

It contains no wallet secret, signer, live endpoint, or mutable runtime state.

---

# 10. Protocol Constraint Semantics

## 10.1 Twenty-five-square vector

The canonical protocol deployment is a 25-element vector:

```text
deployed_lamports[0..24]
```

Each element is either:

- zero, meaning the authority did not deploy on that square; or
- a positive integer lamport amount.

The vector, not “number of miners,” is the primary deployment object.

## 10.2 Occupied squares

Within one authority and round, a square with a positive recorded deployment
is occupied.

The simulation shall not:

- top up that square;
- replace its amount;
- create a second participant allocation on it; or
- count another transaction as another square placement.

The participant may occupy at most 25 squares in one round.

## 10.3 Checkpoint requirement

An authority may begin deployment in a new round only if the previous Miner
round has been checkpointed according to the selected protocol revision.

Checkpoint is a state transition with:

- eligibility;
- cost;
- settlement effects; and
- a deterministic result.

If the prior round cannot be economically settled, the stateful simulation
must not silently mark it checkpointed.

## 10.4 Deployment timing

The deployment decision occurs at the historical Decision Context boundary.

The Economic Scenario defines a deterministic mapping from:

- decision slot;
- planned transaction work; and
- configured inclusion latency

to an assumed inclusion slot.

A deployment that would not be included before the protocol deadline is
rejected. It is not moved earlier or later to obtain a favorable result.

## 10.5 Transaction inclusion

Inclusion is a modeled assumption, not an observed fact, unless the replay
dataset contains direct evidence for the simulated participant transaction.

The inclusion model must be:

- deterministic;
- independent of future outcome;
- fixed before experiment execution;
- versioned and hash-bound; and
- reported with every result.

RFC-011 does not model stochastic mempool or validator behavior.

## 10.6 Counterfactual market state

RFC-011 models a synthetic participant whose deployment is not already present
in the historical aggregate.

The simulation:

- inserts the synthetic deployment at the modeled inclusion point;
- adds it to the applicable historical per-square totals;
- preserves the historical entropy and winning square;
- recalculates settlement quantities affected by the added capital; and
- does not remove or relabel any historical participant.

The simulation must not double-count a known historical participant position.
Simulating an identified historical wallet is outside RFC-011.

---

# 11. Economic Result Semantics

Each Economic Round Result records facts in four groups.

## 11.1 Feasibility

- requested budget;
- deployable budget;
- materialized 25-square vector;
- occupied square count;
- instruction count;
- transaction count;
- inclusion status;
- rejection reason, if any; and
- checkpoint eligibility.

## 11.2 Capital flows

- SOL deployed;
- SOL principal returned;
- SOL winnings returned;
- protocol fees;
- transaction and priority fees;
- checkpoint costs;
- gross SOL outflow;
- gross SOL inflow; and
- net SOL change.

## 11.3 ORE result

- ORE earned;
- split or solo reward classification;
- participant share of a split reward;
- winning-square capital share;
- dilution; and
- capture efficiency.

## 11.4 Provenance

- replay round identity;
- decision identity;
- Evaluation Result identity;
- finalized outcome identity;
- outcome source (`observed` or `enriched`);
- protocol revision;
- scenario identity; and
- completeness status.

No result may imply that an enriched outcome was available to Strategy at
decision time.

---

# 12. Metrics Hierarchy

## 12.1 Capital metrics

RFC-011 may aggregate:

- total lamports deployed;
- mean lamports deployed per settled round;
- maximum concurrent SOL exposure;
- deployment-budget utilization;
- total protocol fees;
- total transaction fees;
- total checkpoint costs;
- total SOL returned; and
- net SOL change.

## 12.2 Reward metrics

RFC-011 may aggregate:

- total ORE earned;
- mean ORE earned per settled round;
- ORE earned per SOL deployed;
- solo reward frequency;
- split reward frequency;
- average winning-square share;
- average dilution; and
- capture efficiency.

“Expected ORE” in RFC-011 means the deterministic historical sample mean over
the economically settled replay rounds. It is not a forward-looking market
forecast.

## 12.3 Return metrics

RFC-011 does not define one combined, unqualified “ROI.”

It may report:

- **net SOL return rate**, calculated only from SOL-denominated flows; and
- **ORE yield per SOL committed**, which preserves the two native units.

It shall not calculate a total economic ROI that adds or converts ORE and SOL
without an external valuation model. Market-valued ROI remains outside
RFC-011.

## 12.4 Existing RFC-010 metrics

RFC-010 hit rate, miss rate, evaluation count, and selection distribution
remain unchanged.

RFC-011 metrics supplement them. They do not overwrite or reinterpret the
RFC-010 Experiment Metrics.

---

# 13. Outcome Completeness and Replay Readiness

The
[Dataset Management Investigation](../research/dataset-management-investigation.md)
and
[Outcome Provenance Investigation](../research/outcome-provenance-investigation.md)
establish that dataset integrity and finalized-outcome completeness are
separate properties.

RFC-011 preserves that distinction.

## 13.1 Per-round settlement

An economic result may be settled only when the round has sufficient
authoritative finalized data for the selected protocol model.

If finalized data is missing:

- the round is economically unevaluable;
- no reward or return is fabricated;
- no favorable or unfavorable outcome is imputed; and
- the missing result is reported explicitly.

## 13.2 Stateful continuity

Participant balance and checkpoint state are sequential.

A stateful economic simulation may continue across a round only when that
round's capital flow can be settled deterministically. A missing settlement
breaks economic continuity.

The simulation must not skip an unsettled round and pretend the later wallet
balance is known.

Outcome-complete contiguous intervals may be simulated independently when
their initial Participant Economic State is explicit and immutable.

## 13.3 Outcome provenance

Observed and enriched outcomes may both support settlement when they satisfy
dataset integrity and protocol-state requirements.

Every result must retain the source distinction.

The economics layer never:

- performs enrichment;
- calls RPC;
- rewrites observer history; or
- upgrades a missing outcome to a finalized one.

---

# 14. Determinism and Reproducibility

Given identical:

- RFC-010 experiment artifacts;
- replay dataset;
- Economic Scenario;
- ORE protocol revision;
- initial Participant Economic State;
- component versions; and
- finalized outcomes,

RFC-011 shall produce identical:

- materialized lamport vectors;
- feasibility decisions;
- transaction plans;
- inclusion decisions;
- settlement results;
- state transitions;
- metrics; and
- Economic Simulation Record hashes.

Determinism prohibits dependence on:

- live RPC;
- wall-clock time;
- current network fees;
- current market prices;
- map or filesystem ordering;
- machine floating-point behavior;
- random transaction inclusion;
- mutable configuration; or
- production state.

Every assumption that can affect an economic result must be immutable,
versioned, and included in the simulation identity.

---

# 15. Failure Semantics

RFC-011 fails closed when:

- an allocation is malformed or economically incompatible;
- allocation shares exceed the configured budget;
- deterministic lamport materialization is impossible;
- square identity is invalid or duplicated;
- an occupied square would be redeployed;
- the participant lacks required SOL or reserves;
- prior checkpoint state is invalid;
- a transaction plan violates the selected protocol model;
- modeled inclusion misses the round deadline;
- protocol revision identity is missing or mismatched;
- finalized outcome data is insufficient;
- outcome and RFC-010 Evaluation Result disagree;
- historical deployment would be double-counted;
- state continuity is broken;
- provenance is missing;
- an economic component identity is unknown; or
- reproduction hashes do not match.

Failure produces no inferred economic success and no mutation of an earlier
immutable result.

---

# 16. Invariants

RFC-011 shall preserve:

- all RFC-010 interfaces and responsibilities;
- deterministic replay;
- no future-information leakage;
- Strategy purity;
- Deployment Model independence;
- Evaluator independence;
- immutable experiments;
- exact integer monetary accounting;
- explicit participant budget;
- one 25-square vector per modeled authority and round;
- one positive deployment per authority–round–square;
- protocol-versioned settlement;
- deterministic transaction assumptions;
- separate SOL and ORE denominations;
- explicit outcome provenance;
- fail-closed missing-outcome behavior;
- sequential economic-state integrity;
- no production reachability;
- no wallet, signer, transaction, or network capability; and
- reproducibility from immutable artifacts.

---

# 17. Repository and Governance Boundaries

RFC-011 is an offline Research Domain architecture.

Its implementation and artifacts shall:

- read only immutable Research Domain replay artifacts;
- consume RFC-010 experiment outputs;
- write only Research Domain economic simulation artifacts;
- never import or invoke production entry points;
- never modify production ledgers or authorizations;
- never become part of the Production Release Closure implicitly; and
- cross into Production only through the explicit Promotion Domain.

An RFC-011 result does not authorize:

- paper collection;
- live collection;
- capital deployment;
- transaction submission;
- a production strategy;
- a wallet budget; or
- any operational release.

---

# 18. Explicitly Outside RFC-011

The following remain outside this architecture:

## Market and portfolio concepts

- ORE/SOL or fiat price;
- mark-to-market valuation;
- combined economic profit;
- USD ROI;
- volatility-adjusted return;
- portfolio optimization;
- capital allocation across protocols;
- borrowing, leverage, or liquidity management.

## Live operational concepts

- wallet discovery;
- wallet balances from a network;
- signer selection;
- key custody;
- transaction building;
- simulation against a live validator;
- submission or confirmation;
- retry policy;
- live fee bidding;
- live congestion response;
- claims or swaps;
- production kill switches.

## Strategy and learning concepts

- new Strategy semantics;
- strategy access to budget or economic state;
- adaptive capital management;
- automatic strategy ranking or selection;
- machine learning;
- reinforcement learning.

## Data concepts

- observer collection;
- finalized-outcome persistence;
- outcome enrichment;
- dataset repair;
- synthetic finalized outcomes;
- changing Replay semantics.

## Identity concepts

- linking multiple authorities to one human;
- sybil detection;
- coordinated multi-wallet deployment;
- custody or organizational ownership.

---

# 19. Success Criteria

RFC-011 is complete when a researcher can select:

- one immutable RFC-010 experiment;
- one immutable Economic Scenario;
- one supported ORE protocol revision; and
- one explicit initial Participant Economic State,

and deterministically produce:

- an exact protocol-feasible lamport deployment for every evaluable decision;
- explicit rejection for every infeasible decision;
- protocol-native SOL and ORE settlement for every outcome-complete round;
- sequential participant economic state without hidden capital injection;
- aggregate capital, reward, dilution, and efficiency metrics;
- a completeness and provenance report; and
- an immutable, reproducible Economic Simulation Record.

Completion must not require any modification to RFC-010 components.

---

# 20. Architectural Conclusion

RFC-010 remains responsible for historical decision quality:

```text
Replay → Strategy → Deployment → Evaluation
```

RFC-011 adds a downstream economic interpretation:

```text
Deployment Decision
        +
Evaluation Result
        +
Replay Facts
        +
Economic Scenario

        ↓

Protocol-Faithful ORE Economic Simulation
```

`allocation_amount` remains an abstract RFC-010 output and becomes a
dimensionless share of an explicit participant deployment budget only at the
RFC-011 boundary.

The budget is denominated and accounted in integer lamports. The materialized
deployment is a 25-square lamport vector for one protocol authority. Protocol
constraints, modeled inclusion, settlement, fees, ORE reward, dilution, and
capital efficiency belong to RFC-011.

Market valuation, live wallets, transaction execution, portfolio management,
and production authority do not.

This separation preserves RFC-010 while making economic simulation faithful
to the resource semantics of ORE.
