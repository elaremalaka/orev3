# RFC-012 Implementation Plan

**Status:** Frozen — Implementation-Ready

**Architecture:**
[RFC-012 — Observer Post-Transition Finalization Capture](../../rfcs/RFC-012-OBSERVER-FINALIZATION-CAPTURE.md)

**Revision basis:** Completed RFC-012 Implementation Plan Readiness Review

This document defines implementation sequencing for RFC-012. RFC-012 remains
the sole architectural authority. This plan assigns implementation ownership,
dependencies, validation, and governance gates without adding capabilities or
changing the RFC.

---

# 1. Implementation Principles

RFC-012 introduces one bounded post-transition predecessor observation and one
outcome-only Dataset Builder consumption boundary.

Implementation shall preserve:

- the existing Observer architecture;
- the one-logical-observation budget;
- context-bound acceptance;
- explicit finalized-state validation;
- durable finalized persistence;
- immutable append-only evidence;
- deterministic identities and reconstruction;
- deterministic replay;
- `DecisionContext` and Strategy isolation;
- canonical observed/enriched provenance;
- RFC-011 outcome and missingness semantics;
- reachability-based repository-domain governance; and
- the absence of wallet, signer, transaction, mining, claim, deployment,
  authorization, and production-ledger capability.

Implementation shall not add:

- repeated predecessor reads;
- outcome-specific retries;
- background queues;
- restart recovery;
- concurrent Observer support;
- multi-provider observation;
- historical repair or backfill;
- Replay redesign;
- Dataset redesign;
- Strategy Lab changes;
- RFC-011 changes;
- production operation; or
- a new CLI capability.

Each implementation responsibility has exactly one owning phase. A later phase
may consume or validate an earlier output but may not redefine or reimplement
it.

No phase is complete until its objective Definition of Done, phase-specific
validation, repository-domain classification, and applicable governance checks
all pass.

---

# 2. Repository-Domain and Governance Gate

Repository Architecture classifies changed artifacts by authority and
transitive reachability, not by directory or intent. RFC-012 does not assume
that implementation changes belong exclusively to the Research Domain.

Before each phase begins and again before its commit:

1. enumerate the exact changed artifacts;
2. determine whether any changed artifact is transitively reachable from a
   production entry point;
3. record the resulting domain classification;
4. run the validation required by every affected domain; and
5. apply the existing approval workflow when the Production Release Closure is
   affected.

The gates are:

| Classification | Required validation and governance |
| --- | --- |
| Documentation Domain only | Documentation consistency, links, formatting, and architectural conformance. |
| Research Domain only | Affected tests, deterministic and reproducibility validation, Research Domain tests, and full repository validation. |
| Production Release Closure | All affected and full repository validation, RFC-008 production validation, active-release topology validation, and the applicable RFC-008 approval workflow. RFC-009 applies only if an explicitly authorized continuation operation is later requested; no such operation is part of this plan. |

No phase may claim Research Domain isolation solely because its output is
read-only evidence. Shared Observer, RPC, model, writer, or Dataset code must be
classified from the actual import and execution graph.

All validation in this implementation plan uses controlled deterministic
fixtures. No phase performs production collection, external RPC readiness
testing, wallet access, authorization changes, ledger changes, or an operational
Observer restart.

---

# 3. Five-Phase Dependency Order

```text
Phase 1
Immutable Evidence Contracts

        ↓

Phase 2
Context-Bound Observation and Evidence Persistence

        ↓

Phase 3
Outcome-Only Dataset Builder Consumption

        ↓

Phase 4
Observability and Effectiveness Reporting

        ↓

Phase 5
Supported Runtime Integration and Final System Validation
```

The dependency direction is strict:

- Phase 2 consumes immutable Phase 1 contracts.
- Phase 3 consumes Phase 2's durable evidence output through the Phase 1
  contracts.
- Phase 4 consumes immutable Phase 2 evidence and Phase 3 outcome
  classifications.
- Phase 5 wires the completed Phase 2 behavior into the supported Observer
  runtime and validates the complete Phase 1–4 system.

No phase split is required. The five phases remain independently reviewable
because component behavior and supported-runtime wiring have distinct owners.

---

# 4. Phase 1 — Immutable Evidence Contracts

## 4.1 Objective

Implement the complete immutable semantic interfaces and deterministic
identities defined by RFC-012 Sections 10 through 14 without changing Observer,
RPC, Dataset Builder, replay, or runtime behavior.

## 4.2 Owned responsibilities

Phase 1 exclusively owns:

- immutable transition context representation;
- immutable canonical predecessor identity representation;
- immutable transition-evidence representation;
- immutable post-transition evidence representation;
- terminal-disposition vocabulary;
- validation-outcome and failure-category representation;
- canonical broad outcome source and capture-mode vocabulary;
- canonical protocol payload representation;
- deterministic transition, response, payload, and evidence identities;
- evidence schema and producer identities;
- versioned canonical encoding; and
- deterministic reconstruction and validation of those contracts.

Later phases may populate and validate these types but may not add fields,
change identity inputs, change canonical encoding, or redefine provenance.

## 4.3 Deliverables

Implement immutable public contracts for:

- `TransitionContext`;
- `CanonicalPredecessorIdentity`;
- `TransitionIdentity`;
- `ResponseIdentity`;
- `EvidenceIdentity`;
- `TransitionEvidence`;
- `PostTransitionEvidence`;
- `PreservedProtocolPayload`;
- `TerminalDisposition`;
- validation outcomes and failure categories;
- outcome source `observed` or `enriched`; and
- capture mode `current_round` or `post_transition_predecessor`.

The contracts shall preserve every RFC-012 identity input:

- evidence schema identifier and version;
- producer identity;
- Observer session identity;
- network identity and expected genesis hash;
- ORE program identity and protocol revision;
- Board account identity;
- predecessor Round identifier and canonical PDA;
- expected account owner;
- successor Round and successor snapshot identities;
- redacted provider identity;
- Board response commitment and context slot;
- predecessor response commitment and context slot when present;
- raw account payload and payload hash when present;
- pinned decoder identity;
- decoded Round fields when decoding succeeds;
- validation outcome;
- terminal disposition;
- finalized-state determination; and
- canonical provenance.

Canonical identity construction shall use fixed RFC-012 domain separators and
versioned byte-stable encoding. It shall distinguish an absent response or
payload with explicit canonical markers. It shall exclude attempt timestamps,
RPC URLs, credentials, tokens, query strings, and other secrets.

Raw account bytes and deterministically decoded Round fields shall be preserved
without reinterpretation. Their identities must agree under the pinned decoder
and protocol revision or validation shall fail.

## 4.4 Strict exclusions

Phase 1 performs no:

- Observer loop change;
- RPC call;
- evidence append;
- finalized outcome persistence;
- Dataset Builder change;
- replay change;
- metrics or reporting; or
- runtime integration.

## 4.5 Objective Definition of Done

Phase 1 is complete only when deterministic tests prove:

1. every public contract is immutable;
2. identical canonical inputs produce byte-identical encodings and identities;
3. every normative identity input changes the appropriate identity when
   changed;
4. timestamps and secrets do not affect or enter identities;
5. explicit no-response and no-payload markers cannot collide with present
   empty values;
6. transition, response, payload, and evidence domain separation prevents
   cross-type identity collisions;
7. field declaration, mapping insertion, and input traversal order cannot
   change canonical encoding;
8. raw payload and decoded payload disagreement is rejected;
9. unsupported schema, producer, decoder, program, or protocol identities are
   rejected;
10. canonical provenance accepts only the RFC-012 source/capture-mode values;
11. serialized fixtures reconstruct the same immutable objects and identities;
    and
12. existing Observer, Dataset Builder, replay, Strategy Lab, and RFC-011
    behavior remains unchanged.

## 4.6 Phase-specific validation

Run:

- Phase 1 evidence-contract unit tests;
- immutability and mutation-rejection tests;
- canonical encoding and identity reconstruction tests;
- malformed, missing, unknown-version, and cross-domain identity tests;
- affected Observer/Dataset model compatibility tests;
- compilation;
- formatting validation;
- `git diff --check`;
- domain-required validation from Section 2; and
- full repository validation before commit.

---

# 5. Phase 2 — Context-Bound Observation and Evidence Persistence

## 5.1 Objective

Implement the isolated RFC-012 transition processor that accepts an already
persisted successor observation, performs the bounded predecessor branch, and
produces durable finalized outcome and append-only evidence outputs. Phase 2
does not wire that processor into the supported continuous Observer entry point;
Phase 5 owns that integration.

## 5.2 Owned responsibilities

Phase 2 exclusively owns:

- verified transition-candidate detection;
- read-eligible versus already-durable determination;
- context-preserving Board and predecessor response inputs;
- the one-logical-predecessor-observation branch;
- the objective context acceptance predicate;
- runtime predecessor account validation;
- terminal-disposition selection;
- duplicate prevention through the existing finalized identity semantics;
- durable finalized outcome persistence;
- immutable transition and post-transition evidence persistence;
- canonical append ordering;
- supplementary failure behavior; and
- the durable evidence producer/reader boundary consumed by Phase 3.

Phase 2 owns behavior and persistence. It does not redefine Phase 1 contracts,
consume evidence into datasets, calculate aggregates, or alter the supported
runtime entry point.

## 5.3 Deliverables

Implement an isolated transition processor whose inputs include:

- the previously accepted Round identifier;
- the validated and durably persisted successor snapshot and identity;
- the exact Board response context that supplied the successor Board;
- validated non-secret network, genesis, provider, commitment, program, and
  protocol identities;
- durable finalized-history access; and
- the immutable Phase 1 evidence contracts.

The processor shall:

1. recognize only a verified contiguous `R -> R + 1` transition candidate;
2. derive and validate the canonical predecessor identity;
3. append immutable transition evidence;
4. check durable finalized history;
5. emit `already_durable` and perform zero reads when a valid predecessor final
   already exists;
6. otherwise submit exactly one logical observation for the canonical
   predecessor account;
7. constrain the request not to resolve before the retained Board context slot;
8. require an explicit predecessor response context;
9. require predecessor context slot greater than or equal to Board context
   slot;
10. require the same network, expected genesis, and redacted provider identity;
11. require the same or stronger commitment under
    `processed < confirmed < finalized`;
12. prohibit provider switching within the attempt;
13. apply canonical PDA, owner, program, schema, Round identity, protocol,
    decoder, representability, context, and explicit-finality validation;
14. preserve raw and decoded protocol payload without reinterpretation;
15. persist an explicitly finalized valid outcome through the existing durable
    finalized path;
16. record `finalized_persisted` only after durable persistence succeeds;
17. persist one immutable post-transition evidence record with the truthful
    terminal disposition; and
18. preserve the already accepted successor observation under every branch.

The logical ordering is fixed:

```text
Durable successor snapshot
  -> transition evidence
  -> zero or one predecessor observation
  -> durable finalized outcome when valid
  -> truthful post-transition disposition evidence
```

The durable evidence output shall be discoverable and readable through the
Phase 1 schema without being represented as a current-round snapshot. Physical
storage remains an implementation choice and shall not alter the semantic
contract.

## 5.4 Terminal behavior

The processor shall deterministically produce exactly one applicable terminal
disposition for every completed candidate branch:

- `already_durable`;
- `finalized_persisted`;
- `not_finalized`;
- `account_unavailable`;
- `context_unproven`;
- `invalid_or_ambiguous`; or
- `operational_failure`.

No failed, absent, nonfinal, stale, mismatched, or ambiguous response may become
a finalized outcome. A supplementary failure shall not remove, replace, or
invalidate the accepted successor snapshot.

## 5.5 Strict exclusions

Phase 2 adds no:

- repeated or adaptive predecessor observation;
- outcome-specific retry policy;
- background queue;
- restart recovery;
- concurrent Observer support;
- provider voting or provider switching;
- Dataset Builder behavior;
- replay behavior;
- aggregate metrics;
- CLI; or
- production operation.

## 5.6 Objective Definition of Done

Phase 2 is complete only when controlled fixtures prove:

1. initial, unchanged, skipped, regressed, ambiguous, or invalid successor
   observations issue zero supplementary reads;
2. an already-durable contiguous candidate issues zero reads and records
   `already_durable`;
3. every read-eligible candidate issues exactly one logical predecessor
   observation;
4. the canonical predecessor PDA and full identity are used;
5. the Board context comes from the response that supplied the Board, not a
   separately sampled slot;
6. missing, older, mismatched-network, mismatched-genesis,
   mismatched-provider, and weaker-commitment contexts produce
   `context_unproven` and no finalized outcome;
7. wrong PDA, owner, program, schema, Round identity, protocol revision,
   decoder identity, malformed payload, or raw/decoded disagreement produces
   `invalid_or_ambiguous`;
8. valid nonfinal, unavailable, and operational-failure branches produce their
   exact dispositions without inference;
9. a valid finalized response reaches the existing durable path before
   `finalized_persisted` is recorded;
10. persistence failure never records `finalized_persisted`;
11. append order is exactly the RFC-012 order;
12. transition and post-transition evidence reconstruct through Phase 1
    identities;
13. duplicate finalized persistence remains impossible across repeated
    processing and process restart fixtures;
14. every branch preserves the accepted successor snapshot;
15. no post-transition evidence is emitted as a current-round snapshot; and
16. no wallet, signer, transaction, mining, claim, deployment, authorization,
    or production-ledger capability is reachable.

## 5.7 Phase-specific validation

Run:

- Phase 2 transition-processor unit tests;
- context predicate fixtures for every accepted and rejected relationship;
- zero/one logical observation-count tests;
- predecessor identity and protocol validation tests;
- terminal-disposition decision-table tests;
- durable persistence and canonical append-order tests;
- duplicate and restart fixtures;
- successor-preservation tests;
- controlled failure-injection tests;
- existing Observer finalized-persistence tests;
- affected RFC-008 outcome and Observer tests when reachable;
- compilation;
- formatting validation;
- `git diff --check`;
- domain-required validation from Section 2; and
- full repository validation before commit.

No validation test uses external RPC.

---

# 6. Phase 3 — Outcome-Only Dataset Builder Consumption

## 6.1 Objective

Implement the narrow RFC-012 outcome-source boundary without adding
post-transition evidence to replay snapshots or changing replay, Strategy Lab,
or RFC-011 semantics.

## 6.2 Owned responsibilities

Phase 3 exclusively owns:

- discovery and parsing of Phase 2 evidence for dataset construction;
- evidence integrity and supported-version validation at the consumer boundary;
- canonical predecessor-lifecycle joining;
- outcome-only acceptance after decision snapshots are frozen;
- current-round, post-transition, and enriched source reconciliation;
- broad outcome-source and capture-mode persistence;
- conflict detection and fail-closed behavior;
- compatibility with pre-RFC-012 raw snapshots and replay datasets; and
- proof that post-transition evidence cannot enter decision-time replay state.

Phase 3 does not redefine evidence, identities, context, terminal behavior, or
runtime observation.

## 6.3 Deliverables

The Dataset Builder shall:

1. discover the immutable RFC-012 evidence source separately from normal
   Observer snapshots;
2. reject malformed, unknown-version, identity-invalid, context-invalid, or
   unsupported evidence;
3. freeze the ordered decision-time snapshots for predecessor Round `R` before
   considering post-transition evidence;
4. join only through the complete canonical predecessor identity;
5. accept only `finalized_persisted` evidence whose raw payload hash, decoded
   payload, finality predicate, protocol revision, and predecessor identity
   agree;
6. copy only finalized outcome fields into the existing outcome/evaluation
   position;
7. preserve snapshot history, timestamps, Board/Treasury state, replay order,
   `DecisionContext`, Strategy input, and the RFC-010 outcome-revelation
   boundary;
8. classify an accepted post-transition outcome as
   `finalized_outcome_source = observed` and capture mode
   `post_transition_predecessor`;
9. preserve `finalized_outcome_source = enriched` only for outcomes obtained
   solely through enrichment;
10. preserve capture mode `current_round` for normal locally observed outcomes;
11. retain current-round evidence as canonical when agreeing current-round and
    post-transition payload hashes coexist, while preserving supplementary
    evidence for audit;
12. prefer agreeing local explicit observed evidence over enrichment;
13. fail closed on conflicting current-round, post-transition, or enriched
    canonical outcome payloads; and
14. preserve missing outcomes as missing without fabrication.

Compatibility shall be additive. Existing raw snapshots remain valid input.
Existing replay artifacts are not repaired, rewritten, or silently
reclassified. Rebuilding from pre-RFC-012 normal observations deterministically
produces the existing `observed`/`enriched` result and the canonical
`current_round` capture mode where locally observed evidence exists.

## 6.4 Strict exclusions

Phase 3 creates no:

- replay snapshot from post-transition evidence;
- new decision observation;
- Board or Treasury history change;
- Strategy or `DecisionContext` field;
- historical repair or backfill;
- enrichment-policy change;
- replay redesign;
- Dataset redesign beyond the RFC-012 source and capture-mode extension;
- RFC-011 behavior change; or
- runtime observation.

## 6.5 Objective Definition of Done

Phase 3 is complete only when deterministic fixtures prove:

1. RFC-012 evidence is discovered separately from current-round snapshots;
2. unsupported schema/producer/protocol/decoder identities and malformed
   evidence fail closed;
3. timestamp proximity, file order, or successor identity alone cannot join an
   outcome;
4. only complete canonical predecessor identity joins exactly one lifecycle;
5. outcome acceptance occurs after decision snapshots are frozen;
6. accepted post-transition evidence affects only the predecessor outcome;
7. replay snapshot count, content, and ordering remain unchanged;
8. `DecisionContext` and Strategy-visible inputs remain byte-equivalent with
   and without post-transition evidence;
9. current-round, post-transition, enriched, and missing provenance maps to the
   exact RFC-012 values;
10. agreeing current-round and post-transition evidence resolves to canonical
    `current_round` provenance and retains supplementary audit identity;
11. agreeing local post-transition evidence and enrichment resolves to local
    `observed` provenance;
12. every conflicting canonical payload combination fails closed;
13. old raw snapshots and replay datasets retain their existing behavior;
14. post-transition evidence is never visible before RFC-010 outcome
    revelation; and
15. RFC-011 observed/enriched provenance and missing-outcome behavior remains
    unchanged.

## 6.6 Phase-specific validation

Run:

- Phase 3 evidence discovery and parser tests;
- canonical join and non-join tests;
- outcome-source/capture-mode serialization tests;
- agreeing and conflicting three-source reconciliation tests;
- malformed and unknown-version fail-closed tests;
- pre-RFC-012 compatibility fixtures;
- replay snapshot identity and ordering regression tests;
- RFC-010 `DecisionContext`, Strategy purity, and future-information tests;
- RFC-011 provenance and missing-outcome tests;
- Dataset Builder and Dataset validation suites;
- compilation;
- formatting validation;
- `git diff --check`;
- domain-required validation from Section 2; and
- full repository validation before commit.

---

# 7. Phase 4 — Observability and Effectiveness Reporting

## 7.1 Objective

Produce deterministic, immutable aggregates and bounded effectiveness reports
from Phase 2 evidence and Phase 3 outcome classifications. This phase measures
the system; it does not change observation, persistence, dataset assembly, or
replay behavior.

## 7.2 Owned responsibilities

Phase 4 exclusively owns:

- deterministic per-disposition and transition aggregates;
- immutable bounded-window identity and report boundaries;
- complete RFC-012 operational evidence reporting;
- complete RFC-012 effectiveness reporting;
- evidence-bounded enrichment-avoided calculation; and
- explicit separation of implementation conformance from realized
  effectiveness.

Phase 4 does not own a CLI. Any existing reporting surface may present its
immutable outputs without recomputing them.

## 7.3 Deliverables

Implement deterministic reporting for:

- window identity and start/end boundaries;
- contiguous transition candidates;
- skipped transitions;
- read-eligible candidates;
- already-durable candidates;
- supplementary observations attempted;
- finalized predecessor outcomes persisted;
- valid nonfinal responses;
- unavailable predecessors;
- context-unproven results;
- invalid or ambiguous results;
- operational failures;
- duplicate finalized observations prevented;
- transition-to-observation latency;
- total locally observed finalized outcomes;
- outcomes still requiring enrichment;
- unresolved outcomes;
- attempt success rate;
- every terminal-disposition rate;
- transition outcome distributions; and
- enrichment avoided only where the same bounded dataset build would otherwise
  classify the accepted outcome as `enriched`.

Every aggregate shall be reproducible from immutable identities and evidence.
No aggregate may infer a finalized outcome, mutate evidence or datasets, or
present a realized recovery percentage as an implementation conformance gate.

## 7.4 Objective Definition of Done

Phase 4 is complete only when deterministic fixtures prove:

1. identical evidence, dataset classifications, and window boundaries produce
   byte-identical report content and identity;
2. record traversal or input insertion order cannot change results;
3. every verified candidate and completed disposition is counted exactly once;
4. all required counts and rates reconcile to immutable source identities;
5. failed, absent, nonfinal, stale, or invalid responses are never counted as
   observed outcomes;
6. post-transition observed counts include only capture mode
   `post_transition_predecessor`;
7. enrichment avoided is reported only under the RFC-012 counterfactual rule;
8. missing and unresolved outcomes remain explicit;
9. empty and zero-denominator windows are represented deterministically;
10. report generation modifies no evidence, dataset, replay, Strategy, or
    economic state; and
11. conformance status is independent of any measured recovery percentage.

## 7.5 Phase-specific validation

Run:

- Phase 4 aggregate and reconciliation tests;
- bounded-window identity and boundary tests;
- deterministic ordering and repeated reconstruction tests;
- zero-denominator and empty-window tests;
- provenance and enrichment-avoided tests;
- immutable-input/no-mutation tests;
- affected Dataset and Observer evidence tests;
- RFC-010 and RFC-011 regression tests;
- compilation;
- formatting validation;
- `git diff --check`;
- domain-required validation from Section 2; and
- full repository validation before commit.

No live effectiveness threshold is required to complete Phase 4.

---

# 8. Phase 5 — Supported Runtime Integration and Final System Validation

## 8.1 Objective

Wire the completed Phase 2 transition processor into the existing supported
continuous Observer runtime and prove the complete Phase 1–4 system end to end.
Phase 5 adds no business logic, evidence semantics, dataset behavior, metrics,
or CLI capability.

## 8.2 Owned responsibilities

Phase 5 exclusively owns:

- supported Observer-loop integration;
- dependency wiring among existing Observer components and Phase 1–4 outputs;
- preservation of existing normal snapshot and transition behavior;
- final system conformance validation;
- final RFC-008 through RFC-011 regression validation; and
- final repository-domain and governance verification.

Phase 5 invokes completed components only. It may not duplicate transition
detection, context validation, persistence, Dataset Builder reconciliation, or
report calculation.

## 8.3 Deliverables

Integrate the completed transition processor at the RFC-012 control-flow point:

1. collect and validate the normal successor observation;
2. durably persist the successor snapshot;
3. detect the verified contiguous transition;
4. invoke the Phase 2 processor before remembered-round update, sleep, or the
   next collection iteration;
5. preserve the returned immutable evidence and disposition;
6. update normal Observer transition state; and
7. continue existing collection behavior.

Expose Phase 4 immutable reporting through existing reporting mechanisms only
where already supported. Do not add a new command or place calculations in an
entry point.

The final controlled end-to-end fixture shall exercise:

```text
successor Board response with retained context
  -> durable successor snapshot
  -> verified transition candidate
  -> zero or one predecessor observation
  -> durable finalized outcome when valid
  -> immutable transition and post-transition evidence
  -> outcome-only Dataset Builder consumption
  -> unchanged replay snapshots and DecisionContext
  -> canonical provenance
  -> deterministic operational/effectiveness report
```

## 8.4 Strict exclusions

Phase 5 adds no:

- CLI command;
- transition or validation business logic;
- second evidence writer or identity implementation;
- second Dataset Builder path;
- second metrics engine;
- external RPC validation;
- Observer restart or production launch;
- production artifact mutation; or
- capability excluded by RFC-012.

## 8.5 Objective Definition of Done

Phase 5 is complete only when controlled end-to-end fixtures prove:

1. the successor snapshot is durable before supplementary work;
2. runtime integration invokes Phase 2 exactly once for each verified
   transition candidate;
3. initial, unchanged, skipped, regressed, ambiguous, and already-durable paths
   preserve their exact zero-read behavior;
4. a read-eligible path performs exactly one logical predecessor observation;
5. every accepted result satisfies the complete context and identity contract;
6. valid finalized state is durable before `finalized_persisted`;
7. every failure disposition preserves the successor snapshot and normal loop;
8. Dataset Builder consumption changes only the predecessor outcome;
9. replay snapshots, ordering, `DecisionContext`, and Strategy-visible inputs
   remain unchanged;
10. canonical provenance and conflict behavior remain exact;
11. operational and effectiveness reports reconstruct deterministically;
12. existing pre-RFC-012 collection and dataset fixtures remain compatible;
13. RFC-008 through RFC-011 regression suites pass;
14. repository reachability classification and applicable approval validation
    pass;
15. no excluded capability is reachable; and
16. every RFC-012 Section 23 validation requirement has a passing owner test.

## 8.6 Phase-specific and final validation

Run:

- Phase 5 runtime-integration tests;
- complete RFC-012 end-to-end fixtures;
- all Phase 1–4 tests;
- all Observer tests;
- all Dataset Builder and Dataset validation tests;
- all Replay and Strategy Lab tests affected by outcome ingestion;
- all RFC-011 provenance and missing-outcome tests;
- RFC-008 validation and production-closure tests when reachability requires
  them;
- Research Domain validation for Research-only artifacts;
- full repository validation;
- Python compilation;
- repository formatting and Markdown validation;
- `git diff --check`; and
- clean staged-scope and worktree verification appropriate to the requested
  commit.

All RPC behavior uses controlled fixtures. No production operation occurs.

---

# 9. Complete Responsibility Coverage Matrix

Each implementation responsibility has one owner. Repeated validation of an
earlier invariant does not transfer or duplicate implementation ownership.

| RFC-012 responsibility | Sole owning phase | Consumed or revalidated by |
| --- | ---: | --- |
| Transition context immutable contract | 1 | 2, 5 |
| Canonical predecessor identity contract | 1 | 2, 3, 5 |
| Transition-evidence immutable contract | 1 | 2, 4, 5 |
| Post-transition evidence immutable contract | 1 | 2, 3, 4, 5 |
| Preserved raw/decoded protocol payload contract | 1 | 2, 3, 5 |
| Evidence schema and producer identities | 1 | 2, 3, 5 |
| Transition identity construction | 1 | 2, 3, 4, 5 |
| Response identity construction | 1 | 2, 3, 5 |
| Payload identity construction | 1 | 2, 3, 5 |
| Evidence identity construction | 1 | 2, 3, 4, 5 |
| Canonical encoding and domain separation | 1 | 2–5 |
| Terminal-disposition vocabulary | 1 | 2, 4, 5 |
| Broad outcome-source vocabulary | 1 | 3–5 |
| Capture-mode vocabulary | 1 | 3–5 |
| Verified transition-candidate detection behavior | 2 | 4, 5 |
| Read-eligible/already-durable behavior | 2 | 4, 5 |
| Canonical predecessor runtime validation | 2 | 3, 5 |
| Context-preserving Board/predecessor response handling | 2 | 5 |
| Objective context acceptance predicate | 2 | 3, 5 |
| One-logical-observation enforcement | 2 | 5 |
| Explicit finalized-state validation | 2 | 3, 5 |
| Terminal-disposition selection | 2 | 4, 5 |
| Durable finalized outcome persistence | 2 | 3, 5 |
| Transition/post-transition evidence persistence | 2 | 3–5 |
| Canonical append ordering | 2 | 5 |
| Duplicate prevention and restart behavior | 2 | 5 |
| Supplementary failure behavior | 2 | 5 |
| Durable evidence producer/reader boundary | 2 | 3–5 |
| Dataset evidence discovery and parsing | 3 | 5 |
| Evidence integrity validation at consumption | 3 | 5 |
| Canonical predecessor-lifecycle join | 3 | 5 |
| Outcome-only post-freeze consumption | 3 | 5 |
| Current/post-transition/enriched reconciliation | 3 | 5 |
| Outcome source and capture-mode persistence | 3 | 4, 5 |
| Conflict detection and fail-closed dataset behavior | 3 | 5 |
| Pre-RFC-012 dataset compatibility | 3 | 5 |
| Replay-snapshot and DecisionContext exclusion | 3 | 5 |
| Operational transition/disposition aggregates | 4 | 5 |
| Bounded effectiveness-window identity | 4 | 5 |
| Effectiveness and enrichment-avoided report | 4 | 5 |
| Conformance/effectiveness separation in reporting | 4 | 5 |
| Supported continuous Observer runtime wiring | 5 | — |
| End-to-end RFC-012 system conformance | 5 | — |
| RFC-008 through RFC-011 final regression proof | 5 | — |
| Final no-excluded-capability proof | 5 | — |

Repository-domain classification and applicable governance are mandatory gates
for every phase under Section 2. They are not runtime capabilities and therefore
are not assigned as implementation responsibilities.

---

# 10. RFC-012 Validation Coverage Matrix

| RFC-012 Section 23 requirement | Primary owner test | Final system proof |
| --- | ---: | ---: |
| Successor persisted before supplementary work | 2 | 5 |
| Exactly one logical read for read-eligible candidate | 2 | 5 |
| Zero reads for excluded/already-durable cases | 2 | 5 |
| Canonical predecessor identity | 1 and 2, with non-overlapping contract/runtime tests | 5 |
| Complete objective context predicate | 2 | 5 |
| Existing durable finalized path | 2 | 5 |
| Nonfinal never becomes outcome | 2 | 5 |
| Explicit deterministic terminal disposition | 2 | 5 |
| Duplicate prevention across repetition/restart | 2 | 5 |
| Supplementary failure preserves successor | 2 | 5 |
| Deterministic identity reconstruction | 1 | 5 |
| `finalized_persisted` follows durable success | 2 | 5 |
| Canonical post-freeze Dataset join | 3 | 5 |
| Replay/DecisionContext/Strategy exclusion | 3 | 5 |
| Agreeing/conflicting evidence behavior | 3 | 5 |
| Canonical source/capture-mode mapping | 3 | 5 |
| Replay ordering unchanged | 3 | 5 |
| RFC-010 future-information regression | 3 | 5 |
| RFC-011 provenance/missingness regression | 3 | 5 |
| Reachability classification and RFC-008 validation | Per-phase Section 2 gate | 5 |
| No production capability added | 2 and 3 affected-surface tests | 5 |

The Phase 5 column revalidates integration; it does not reimplement the primary
owner's responsibility.

---

# 11. Per-Phase Exit and Commit Criteria

Before a phase may be declared complete or committed:

1. every deliverable owned by that phase is implemented;
2. every numbered Definition of Done item has a named passing test or objective
   validation artifact;
3. all earlier phase tests continue to pass;
4. all affected component and RFC regression tests pass;
5. changed-artifact reachability classification is recorded;
6. Research Domain or Production Release Closure validation runs as applicable;
7. full repository validation passes;
8. compilation passes;
9. formatting validation and `git diff --check` pass;
10. staged files contain only the authorized phase scope;
11. applicable RFC-008 approval refresh and topology validation complete before
    push when the Production Release Closure is affected; and
12. the worktree status is reported without staging unrelated artifacts.

Push occurs only after explicit push authorization under the repository's
existing operating policy.

---

# 12. Implementation Completion Criteria

RFC-012 implementation is complete when:

- all five phases satisfy their objective Definitions of Done;
- every responsibility in Section 9 has exactly one implemented owner;
- every validation requirement in Section 10 passes;
- the supported Observer runtime invokes exactly the completed Phase 2
  processor at the RFC-012 control-flow boundary;
- immutable evidence reconstructs deterministically;
- finalized persistence and terminal disposition ordering are truthful;
- the Dataset Builder consumes RFC-012 evidence only as predecessor outcome
  evidence;
- replay snapshots, `DecisionContext`, Strategy behavior, and RFC-011 semantics
  remain unchanged;
- deterministic operational and effectiveness reports are reproducible;
- architectural completion remains independent of measured recovery
  percentage;
- repository-domain classification and applicable RFC-008 governance pass;
- no excluded capability is introduced;
- full repository validation and compilation pass; and
- source scope, commit topology, and worktree state satisfy the applicable
  repository governance.

Completion authorizes no production operation, Observer restart, external RPC
diagnostic, dataset rebuild, or effectiveness campaign. Those require separate
explicit operational authorization where applicable.
