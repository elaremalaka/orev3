# RQ-003 Phase 3 — Feature Design Review

## Status

**Type:** Architectural design review

**Domain:** Research

**Implementation authorized:** No

This review defines the principles that every concrete RQ-003 feature must
satisfy before implementation. It creates no feature, feature computation,
dataset, model, strategy, or production authority.

In this document, “production feature” means a production-quality concrete
feature suitable for governed RQ-003 research. It does not mean a feature is
reachable from the repository's Production Domain. RQ-003 remains Research
Domain work unless separately promoted under Repository Architecture.

## Authority

This review is governed by:

- [RQ-003 — Decision-Time Winning-Square Information](../questions/RQ-003-winning-square-predictability.md);
- [RQ-003 Phase 1 — Decision-Time Feature Audit](../questions/RQ-003-feature-audit.md);
- [RQ-003 Phase 2 — Feature Eligibility Resolution](../questions/RQ-003-feature-eligibility-resolution.md);
- [Discovery Session 1 — Dataset Inventory](../notebook/discovery-session-001.md);
- [Discovery Session 2 — Round Evolution](../notebook/discovery-session-002.md);
- [Discovery Session 3 — Round Taxonomy](../notebook/discovery-session-003.md);
- [Discovery Session 4 — Behavioral Dimensions](../notebook/discovery-session-004.md);
- [RFC-010 — Deterministic Strategy Laboratory](../../rfcs/RFC-010-STRATEGY-LAB.md);
- [RFC-011 — ORE Deployment Economics](../../rfcs/RFC-011-ORE-DEPLOYMENT-ECONOMICS.md); and
- [RFC-012 — Observer Finalization Capture](../../rfcs/RFC-012-OBSERVER-FINALIZATION-CAPTURE.md).

This review does not change the eligibility of any feature class. Phase 1 and
Phase 2 eligibility decisions remain authoritative.

## 1. Architectural conclusion

A valid RQ-003 feature is one immutable, terminal-approved semantic contract
and one deterministic implementation of that exact contract. Given the same
authorized decision context and immutable configuration, it produces the same
ordered, canonically encodable output without observing or changing anything
else.

Feature validity has four independent dimensions:

1. **temporal validity:** every input existed at or before the frozen decision;
2. **semantic validity:** input meaning, output meaning, history, arithmetic,
   missingness, and ordering are completely declared;
3. **governance validity:** the exact feature-semantic identity has one terminal
   `approved` eligibility decision; and
4. **execution validity:** the implementation conforms to the declared
   metadata and reconstructs the approved executable binding.

Passing one dimension does not imply another. A deterministic feature can
still leak chronology or outcomes. An eligible class does not automatically
approve every formula in that class. Implemented code does not grant itself
eligibility. Predictive performance does not cure a boundary violation.

## 2. Guiding principles

### 2.1 Decision-time purity

The decision snapshot freezes before any outcome is revealed. A feature may
read only paths declared in its metadata and exposed through the immutable
RQ-003 context for that decision.

Permitted temporal sources are limited to:

- the selected normal observation at the decision boundary;
- earlier normal observations from the same round when the exact approved
  history policy permits them; and
- immutable predeclared configuration.

Post-transition RFC-012 evidence, current-round finalized evidence, historical
enrichment, and all outcome fields converge only at the outcome boundary.
They never enter feature computation. RFC-010's `DecisionContext` and Strategy
boundary remain unchanged.

### 2.2 Determinism

Identical context identity, approved history identity, configuration identity,
metadata identity, and implementation identity must produce byte-equivalent
canonical output and the same validation result.

Results must not depend on:

- wall-clock time;
- random state or entropy;
- network or persistence state;
- process environment, locale, terminal settings, or hash seed;
- filesystem or import discovery order;
- thread scheduling; or
- mutable global or instance state.

If a deterministic result cannot be produced, computation fails closed. It
must not substitute, guess, or emit a partial value.

### 2.3 Deep immutability

Metadata, configuration, history policy, definition binding, and emitted
values are immutable artifacts. Mutable input aliases are not retained.

A computation cannot mutate:

- the current observation;
- historical observations;
- feature configuration;
- registry state;
- another feature's state; or
- any downstream Strategy, Deployment, Evaluation, or Economics state.

Caching may exist only outside feature semantics as a verified, disposable
implementation optimization. A cache must be keyed by complete immutable
input identities, must return canonically identical results, and must never be
visible to a feature. A feature-owned mutable cache is prohibited.

### 2.4 Atomicity

One feature should represent exactly one measurable concept.

A feature may expose multiple ordered output fields only when all outputs:

- are inseparable parts of one documented computation;
- use the same input and history boundary;
- share one eligibility class and semantic lifecycle;
- have explicit individual names, units, types, and nullability; and
- can be validated atomically.

Independent concepts require independent definitions. A multi-output feature
must either emit its complete valid output or emit nothing. Partial output is
never valid.

### 2.5 Measurement before interpretation

A feature measures one observable property of decision-time state. It does
not classify that state, interpret its significance, score a candidate, or
predict an outcome.

Interpretation belongs only to downstream ranking procedures, evaluation, and
Strategy. Keeping measurement separate from interpretation prevents a feature
definition from silently embedding a research conclusion, decision rule, or
predictive claim.

### 2.6 Composability without implicit dependency

Registered features do not consume outputs of other registered features.
Every feature derives its outputs directly from its declared context paths and
immutable configuration.

Features may reuse pure calculation primitives when those primitives:

- have no state or side effects;
- are fully covered by each consuming feature's semantic and implementation
  identities;
- do not access additional context paths; and
- do not make registration order affect meaning.

The current architecture does not define a feature-dependency graph. Allowing
one feature to read another feature's output would introduce undeclared
ordering, transitive-input, identity, failure, and eligibility semantics.
Therefore runtime feature-to-feature dependencies are prohibited. Supporting
them later would require explicit architectural review rather than an
implementation shortcut.

### 2.7 Reproducibility

A persisted feature value must be reconstructable from immutable source and
identity material. At minimum, reconstruction binds:

- decision-snapshot identity;
- allowed-history identity;
- immutable configuration identity;
- feature-semantic identity;
- feature-definition identity;
- terminal eligibility-decision identity; and
- executable-feature binding identity.

Operational details such as duration, machine, or worker count may be recorded
for diagnostics but cannot alter authoritative output or identity.

### 2.8 Explainability

Every feature must be understandable without inspecting model performance.
Its metadata must state neutrally:

- the measurable concept;
- exact source paths;
- formula and arithmetic rules;
- history window and missing-history behavior;
- tie, zero-denominator, and zero-variance behavior where applicable;
- output names, order, types, units, scope, and nullability; and
- any immutable configuration.

Explainability is a semantic contract, not a usefulness claim. Metadata must
not contain feature importance, outcome correlation, strategy admission, or a
recommendation. RFC-010 Strategy explanations remain a separate downstream
artifact.

### 2.9 Canonical identity

Any change capable of changing output or its meaning creates a new identity.
This includes changes to inputs, formula, output schema, ordering, history,
ties, missingness, arithmetic, configuration, or implementation.

The identities remain separated by responsibility:

- semantic identity binds declared behavior but not code;
- definition identity binds one implementation to those semantics;
- eligibility-decision identity binds reviewed authority;
- executable binding joins one definition to its terminal approved decision;
  and
- registry and feature-set identities bind explicit order and membership.

No identity may be reused after a semantic or implementation change. Stored
identities must reconstruct from canonical material; mismatch fails closed.

### 2.10 Explicit history semantics

History is data, not hidden state. Every historical feature must declare:

- whether it reads only the current observation or same-round history through
  the current observation;
- exact bounded length or full-through-current semantics;
- whether contiguous observations are required;
- missing and insufficient-history disposition;
- required slot or wall-clock spans used for validation; and
- cadence assumptions authorized by the eligibility decision.

History ends at the frozen decision observation. No later observation may be
used to complete a window. Availability flags and observation-count features
remain rejected. Cadence-sensitive temporal, rolling-window, leader-history,
reward-derived, and earlier-round-state classes remain deferred unless a new
reviewed decision approves exact semantics.

### 2.11 Ownership and ordering

Every output name has exactly one owner in a frozen registry. Duplicate names,
duplicate semantic identities, duplicate definition identities, ambiguous
aliases, or overlapping output ownership fail closed.

Registry order is supplied explicitly and is identity-bearing. A feature must
not infer meaning from its registry position, the presence of neighboring
features, or execution order. Reordering creates a different registry and
feature-set identity; it must not change an individual feature's result.

### 2.12 Validation before evaluation

Feature conformance is established before any outcome-based evaluation.
Validation uses fixed fixtures, boundary-negative cases, and identity
reconstruction. Winning outcomes must not be used to choose formulas, repair
metadata, resolve missingness, or decide whether a feature is valid.

## 3. Required feature properties

Every concrete feature must satisfy all of the following.

| Property | Required proof |
|---|---|
| Exact eligibility | Its semantic identity resolves to exactly one terminal `approved` decision. |
| Context restriction | It can access only declared paths from the immutable RQ-003 context. |
| Temporal closure | Every current and historical input is at or before the decision freeze. |
| Pure computation | Identical inputs produce identical outputs with no side effects. |
| Atomic output | It emits the complete declared ordered schema or fails without output. |
| Type safety | Every value matches declared scalar type and nullability. |
| Numeric validity | Numeric output is finite and uses declared integer or binary64 rules. |
| Explicit edge cases | Ties, zeros, missing values, and insufficient history have declared behavior. |
| Canonical encoding | Output and identity material encode without ambiguity. |
| Identity reconstruction | Semantic, definition, eligibility, and executable identities reconstruct. |
| Unique ownership | Names and outputs do not collide or alias existing definitions. |
| Environment independence | Locale, hash seed, process state, and scheduling do not affect results. |
| Neutral documentation | Metadata describes semantics without performance or usefulness claims. |
| Boundary-negative validation | Prohibited and future sources are rejected rather than ignored or coerced. |

Failure of any property makes the feature ineligible for registration and
execution.

## 4. Feature groups

Feature groups are a controlled organizational vocabulary for ownership,
eligibility review, validation, and reporting. They are not predictive inputs,
execution namespaces, automatic feature selectors, or grants of eligibility.

Each definition has one primary group. A group should represent a shared
semantic and validation concern, such as:

- `raw_current_state`;
- `current_board_relative`;
- `relative_protocol_timing`; or
- `pre_finalization_aggregate`.

Deferred and rejected groups remain representable as governance history but
cannot enter an executable registry. A group-level approval never approves a
new formula automatically. The exact feature-semantic identity still requires
one reviewed decision.

Changing a definition's group changes its semantic identity. Group ordering is
for deterministic reporting only and must not affect computation or Strategy
behavior.

## 5. Responsibility boundaries

### 5.1 Feature metadata

Metadata owns the complete declarative contract:

- logical name, semantic version, group, and neutral description;
- ordered input paths;
- history and missingness policy;
- ordered output schema, units, scope, ties, and canonical encoding;
- determinism and arithmetic contract;
- immutable configuration identity;
- implementation digest; and
- authority references and reconstructable identities.

Metadata does not own runtime values, evaluation results, performance, or
registration order.

### 5.2 Feature definition

The immutable definition owns the association between one exact metadata
contract and one reviewed implementation identity. Before concrete
implementation binding, the definition remains metadata-only.

The definition does not own eligibility policy, registry order, context
construction, dataset persistence, or downstream use.

### 5.3 Feature computation

Computation owns one pure mapping from an authorized immutable context view to
the exact declared ordered outputs.

Computation does not own:

- its own eligibility;
- undeclared input discovery;
- history selection beyond its declared view;
- output naming or schema changes;
- registry state;
- persistence;
- outcome revelation;
- feature selection; or
- model, Strategy, Deployment, Evaluation, or Economics behavior.

### 5.4 Registry and eligibility

The eligibility catalog determines whether exact semantics are approved. The
frozen registry determines explicit membership, ordering, output ownership,
and registry/feature-set identities. Neither computes feature values.

## 6. Explicitly prohibited behavior

An RQ-003 feature must never:

- read a winning square, `won`, finalized state, outcome availability,
  provenance, capture mode, RFC-012 evidence, or enrichment;
- read any observation after the selected decision snapshot;
- read Replay selection internals, completed-lifecycle counts, collection
  identity, dataset location, or RFC-011 outputs;
- expose raw round, square, participant, collector, dataset, or absolute
  chronology identities as predictive values;
- use `mass`, which the audited dataset establishes as constant zero;
- fabricate, impute, backfill, or silently coerce missing input;
- use mutable hidden state, instance caches, global caches, or prior execution
  results as semantic input;
- call network, persistence, clock, random, environment, or process services;
- depend on another registered feature's runtime output;
- depend implicitly on registry or import order;
- emit undeclared, partial, reordered, wrong-type, or non-finite output;
- duplicate an existing semantic concept or output owner under an alias;
- change behavior without changing the appropriate identities;
- interpret group membership as approval;
- select itself based on outcome performance; or
- influence Replay, Strategy state, Deployment, Evaluation, or RFC-011
  Economics.

## 7. Architectural recommendations

1. Keep each initial concrete feature context-direct and stateless. Reuse only
   pure calculation helpers, never feature outputs.
2. Require one reviewed metadata artifact before implementation begins. The
   artifact should make every edge case testable without consulting results.
3. Bind implementations only after the exact semantic identity is terminally
   approved. Unknown, rejected, deferred, superseded, or ambiguous decisions
   fail closed.
4. Treat multi-output definitions as exceptional and require proof that the
   outputs are one atomic measurable concept.
5. Preserve integer quantities as integers. Use declared exact binary64
   canonical rules only where ratios or standardized values require them.
6. Validate future-information exclusion adversarially, not only by inspecting
   normal fixtures.
7. Keep cadence, lifecycle completeness, outcome provenance, and capture mode
   beside research results as controls only. Never expose them through feature
   accessors.
8. Do not populate an executable registry merely because a feature is
   implemented. Registration requires the exact terminal approval and all
   conformance evidence.

## 8. Definition of Done for Phase 3

Phase 3 is complete only when the implementation enforces this design without
creating or implicitly approving concrete feature semantics.

Objective completion requires:

1. a path-restricted immutable feature-visible context that contains only the
   selected decision observation and explicitly authorized history;
2. a proven freeze boundary ending at the selected normal observation;
3. explicit exclusion of outcomes, RFC-012 evidence, enrichment, controls,
   collection identities, Replay internals, and later observations;
4. per-definition enforcement of declared input paths and history policy;
5. no feature-to-feature runtime dependency surface;
6. deterministic context and history identity reconstruction;
7. fail-closed rejection of unknown paths, prohibited sources, cross-round
   history, noncontiguous required history, and future observations;
8. adversarial tests for every prohibited source class;
9. repeated reconstruction tests across differing hash seeds and environment
   presentation settings;
10. compatibility tests proving RFC-010 `DecisionContext`, Strategy,
    Deployment, and Evaluation remain unchanged;
11. compatibility tests proving RFC-012 evidence remains outcome-only; and
12. confirmation that no feature computation, feature population, dataset,
    model, baseline evaluation, or strategy logic was introduced as part of
    the boundary implementation.

Each later concrete feature must additionally satisfy the complete property
matrix in Section 3 before it may enter a frozen executable registry.

## 9. Review conclusion

The current RQ-003 architecture supports concrete features without redesign
provided they remain atomic, context-direct, stateless, terminally approved,
canonically identified, and independently reproducible. Runtime
feature-to-feature dependency is outside the current architecture and must not
be inferred from registry order.

These principles preserve the essential separation:

```text
Frozen decision-time state
        |
        v
Approved deterministic features
        |
        v
Strategy-visible feature values

Outcome and RFC-012 evidence -----------------> Evaluation only
RFC-011 economics ----------------------------> Downstream only
```

No concrete feature is created or authorized by this review.
