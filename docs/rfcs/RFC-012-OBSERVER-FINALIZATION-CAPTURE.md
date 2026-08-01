# RFC-012 — Observer Post-Transition Finalization Capture

**Status:** Final Draft — Implementation-Ready

**Scope:** Passive Observer architecture; implementation governance is
classified by Repository Architecture reachability

**Canonical document:** This file is the sole normative RFC-012 text. It
supersedes every earlier RFC-012 working draft.

---

# 1. Purpose

RFC-012 defines a narrow architectural enhancement to the ORE Miner V3
Observer.

The enhancement introduces one deterministic, context-bound observation of the
predecessor Round immediately after the Observer confirms that the Board has
advanced to its successor.

The objective is to improve local observation of protocol-finalized state while
preserving every architectural invariant established by RFC-008 through
RFC-011.

RFC-012 extends the existing Observer.

It does not redesign it.

It does not redesign Replay, Strategy Lab, Dataset Management, Economics,
governance, or production authority. Its only Dataset Builder effect is the
outcome-only consumption boundary defined in Section 13.

---

# 2. Design Principle

RFC-012 exists to increase the probability of **observing**
protocol-finalized state.

It does **not** infer, predict, synthesize, reconstruct, or otherwise create
finalized outcomes.

Every accepted finalized outcome shall continue to originate from an explicit
protocol observation.

Board advancement alone is never evidence of finalization.

The additional predecessor observation is therefore an opportunity to observe
already-finalized protocol state rather than permission to infer it.

This principle governs every architectural decision contained in RFC-012.

---

# 3. Evidence Basis

RFC-012 is derived entirely from completed repository investigations.

The following documents are authoritative:

- [Observer Persistence Validation — Version 1.0.1](../research/observer-persistence-validation-v1.0.1.md)
- [Research Question 002 — Post-Transition Finalization](../research/research-question-002-post-transition-finalization.md)

No architectural requirement in RFC-012 is introduced without evidence from
those investigations.

## 3.1 Observer persistence

Version 1.0.1 established that:

- durable finalized persistence functions correctly;
- malformed historical records no longer interrupt finalized persistence;
- finalized observations are persisted exactly once;
- duplicate prevention remains correct; and
- the persistence path is no longer the limiting factor in local outcome
  capture.

The remaining observation gap therefore exists **before persistence**.

## 3.2 Observer transition behavior

Research established that:

- the Observer reads the Board before selecting a Round account;
- the decoded Board round immediately determines which Round account is read;
- once the Board exposes the successor Round, the Observer immediately begins
  observing that successor;
- transition detection occurs only after the successor snapshot has already
  been written; and
- no deliberate observation of the predecessor Round occurs after transition.

## 3.3 Protocol behavior

Research further established from the pinned official ORE implementation that:

- Reset finalizes the predecessor Round;
- Reset creates the successor Round;
- Reset advances the Board;
- those state changes commit atomically within one Solana transaction; and
- the predecessor Round remains readable until its protocol-defined expiry.

Consequently, a confirmed Board response identifying the successor implies that
the predecessor should already exist in finalized form within the same committed
protocol state.

## 3.4 Architectural consequence

Current collection can therefore miss finalized protocol state even when
finalized persistence functions perfectly.

The architectural opportunity addressed by RFC-012 is not persistence.

It is observation.

---

# 4. Goals

RFC-012 shall:

1. introduce one bounded opportunity to observe a just-completed predecessor
   Round;
2. preserve the existing current-round observation loop;
3. perform the additional observation at one deterministic point in the
   existing control flow;
4. preserve durable finalized persistence;
5. preserve append-only evidence;
6. preserve explicit provenance;
7. preserve deterministic replay;
8. preserve fail-closed validation;
9. preserve reachability-based repository-domain isolation;
10. preserve every architectural invariant established by RFC-008 through
    RFC-011; and
11. produce measurable evidence regarding improvement in locally observed
    finalized outcomes.

---

# 5. Non-Goals

RFC-012 does not define:

- repeated predecessor polling;
- retry-based outcome acquisition;
- background observation queues;
- historical reconstruction;
- historical enrichment;
- replay changes;
- Dataset Management changes beyond the outcome-only consumption boundary in
  Section 13;
- Strategy Lab changes;
- RFC-011 Economics changes;
- wallet access;
- signer access;
- transaction construction;
- transaction submission;
- mining;
- claims;
- paper execution;
- live execution;
- production authority; or
- production release behavior.

RFC-012 introduces one additional observation opportunity only.

Nothing more.

---

# 6. Architectural Position

RFC-012 extends only the passive Observer transition boundary.

The existing observation lifecycle remains:

```text
Read Board

↓

Select current Round

↓

Read current Round

↓

Persist current snapshot

↓

Detect transition

↓

Continue
```

RFC-012 introduces one bounded architectural branch:

```text
Read Board

↓

Read and persist successor snapshot

↓

Detect contiguous transition

↓

Persist transition evidence

↓

If predecessor final is not already durable:

    Perform one context-bound predecessor observation

↓

Persist finalized predecessor evidence when valid

↓

Record terminal disposition

↓

Continue normal observation
```

The existing successor observation remains the primary observation path.

The additional predecessor observation supplements that path. It never replaces,
delays persistence of, or modifies the accepted successor observation.

---

# 7. Transition Definition

RFC-012 evaluates one supplementary branch following a verified contiguous
Board transition.

A verified transition candidate exists only when all of the following are true:

1. the Observer has previously accepted Board round identifier `R`;
2. the current observation contains Board round identifier `R + 1`;
3. the successor snapshot has already passed existing validation and durable
   persistence;
4. the transition is contiguous and unambiguous;
5. the predecessor Round identity can be derived canonically from `R`.

The candidate becomes read-eligible only when no durable finalized observation
already exists for predecessor Round `R`. An already-durable candidate consumes
zero reads and terminates as `already_durable`.

RFC-012 performs no supplementary observation for:

- the first observation of a session;
- unchanged Board identifiers;
- regressed Board identifiers;
- skipped transitions;
- ambiguous predecessor identity;
- failed successor validation; or
- already-persisted finalized predecessor evidence.

The last case is a verified candidate but not a read-eligible attempt. It still
produces the `already_durable` disposition required for complete transition
accounting.

Skipped transitions remain explicit observational evidence.

RFC-012 does not attempt to infer which intermediate rounds should be
recovered.

---

# 8. Observer Control Flow

RFC-012 introduces exactly one additional architectural branch into the
existing Observer loop.

The required execution order is:

1. collect and validate the current successor snapshot;
2. durably persist that successor snapshot;
3. determine whether a contiguous transition occurred;
4. persist transition evidence;
5. determine whether finalized predecessor evidence already exists;
6. if not, perform one bounded predecessor observation;
7. classify the observation;
8. persist finalized predecessor evidence when appropriate;
9. update Observer transition state; and
10. continue normal collection.

The successor observation always remains authoritative for the iteration.

The supplementary predecessor observation may never delay, replace, or
invalidate the accepted successor observation.

```text
Current Observation

        ↓

Persist Successor Snapshot

        ↓

Transition Detected?

        ↓

No ───────────────► Continue

        │

       Yes

        ↓

Already Durable?

        ↓

Yes ──────────────► Record disposition

        │

        No

        ↓

One predecessor observation

        ↓

Classify result

        ↓

Persist finalized evidence (when valid)

        ↓

Record terminal disposition

        ↓

Continue normal observation
```

---

# 9. Observation Budget

RFC-012 permits at most one logical predecessor observation for each
read-eligible contiguous transition candidate.

That budget is consumed when the Observer submits the predecessor account
observation.

RFC-012 introduces no:

- repeated polling;
- retry loop;
- delay;
- backoff;
- background queue;
- restart recovery; or
- secondary outcome acquisition mechanism.

A transition therefore produces either:

- zero additional observations; or
- one additional observation.

Never more.

---

# 10. Context-Bound Observation

The predecessor observation must be bound to the protocol transition that
triggered it.

The accepted successor Board response establishes the transition context. That
context consists of:

- the configured network identity and expected genesis hash;
- the configured, non-secret provider identity;
- the Board account identity;
- the predecessor and successor Round identifiers;
- the successor snapshot identity;
- the response commitment; and
- the Board response context slot.

The Board response context slot must come from the response that supplied the
Board account used to select successor Round `R + 1`. A separately sampled slot
is not a substitute.

The predecessor observation is context-valid if and only if all of the
following are true:

1. the predecessor request names the canonical predecessor Round PDA for `R`;
2. the request is constrained not to resolve before the retained Board response
   context slot;
3. the predecessor response supplies an explicit response context slot;
4. that response context slot is greater than or equal to the Board response
   context slot;
5. the response uses the same configured network identity, expected genesis
   hash, and provider identity as the transition observation;
6. the response commitment is the same as, or stronger than, the Board response
   commitment under the fixed order `processed < confirmed < finalized`; and
7. the returned account passes the identity and protocol validation in Section
   11.

The provider identity is a redacted configuration identity, never a URL,
credential, token, or query string. RFC-012 does not authorize provider
switching or multi-provider comparison within one transition attempt.

If that relationship cannot be established:

- finalized evidence is rejected;
- the terminal disposition is `context_unproven`;
- no retry is initiated by RFC-012; and
- normal successor observation continues.

Missing response context, network mismatch, provider mismatch, weaker
commitment, or an older response context all fail this predicate. No
implementation may replace the predicate with wall-clock ordering, request
ordering, or an unconstrained later RPC call.

---

# 11. Observation Validation

The predecessor observation shall satisfy the same validation requirements as
every existing finalized observation.

Validation includes:

- canonical predecessor Round identifier;
- canonical Round PDA;
- expected account owner;
- supported account schema;
- valid decoded Round identity;
- representable protocol fields;
- context validation;
- and the existing finalized-state predicate.

RFC-012 does not redefine finalized state.

Board advancement alone is never interpreted as evidence of finalization.

Only explicit protocol-finalized state may enter durable finalized evidence.

No protocol field is inferred, synthesized, or reconstructed.

---

# 12. Evidence and Provenance

RFC-012 introduces a second observation type:

- current-round observations; and
- post-transition predecessor observations.

Those observation types are intentionally distinct.

## 12.1 Immutable evidence interface

Every verified contiguous transition produces one immutable transition-evidence
record. A transition that reaches the supplementary branch also produces one
immutable post-transition evidence record containing its terminal disposition.

The architectural post-transition evidence interface shall preserve:

- evidence schema identifier and version;
- producer identity;
- Observer session identity;
- deterministic transition identity;
- canonical predecessor identity;
- successor Round identity;
- successor snapshot identity;
- transition context defined in Section 10;
- attempt timestamp;
- response identity when a response exists;
- predecessor response context and commitment when present;
- validation outcome and any failure category;
- terminal disposition;
- finalized-state determination;
- complete preserved protocol payload when decoding succeeds;
- canonical protocol-payload hash; and
- canonical provenance defined in Section 13.

The complete preserved protocol payload consists of the account bytes returned
for the canonical predecessor Round together with the supported, deterministically
decoded Round fields. It is preserved without reinterpretation. The raw payload
hash and decoded representation must agree under the pinned decoder and protocol
revision. A failure to establish that agreement is `invalid_or_ambiguous`.

This section defines a semantic interface only. It does not prescribe a file
format, database, table, or physical storage layout.

## 12.2 Canonical predecessor identity

The canonical predecessor identity is the tuple of:

- network identity and expected genesis hash;
- pinned ORE program identity and protocol revision;
- predecessor Round identifier `R`;
- canonical Round PDA derived for `R`; and
- expected account owner.

All elements must be validated. A numeric Round identifier without its network,
program, PDA, and owner bindings is not a canonical predecessor identity.

## 12.3 Transition identity

The transition identity is the SHA-256 digest of the canonical encoding of:

- a fixed RFC-012 transition domain separator;
- evidence schema version;
- Observer session identity;
- canonical predecessor identity;
- successor Round identifier `R + 1`;
- successor snapshot identity;
- Board account identity;
- configured provider identity;
- response commitment; and
- Board response context slot.

The transition identity never contains secrets or a wall-clock timestamp. The
same accepted transition evidence reconstructs the same identity.

## 12.4 Response and evidence identities

When a predecessor response exists, its response identity is the SHA-256 digest
of the canonical encoding of:

- a fixed RFC-012 response domain separator;
- transition identity;
- canonical predecessor identity;
- predecessor response context slot and commitment;
- raw account payload hash; and
- pinned decoder and protocol revision identities.

For a response-less failure, the response identity is absent rather than
fabricated.

The evidence identity is the SHA-256 digest of the canonical encoding of:

- a fixed RFC-012 evidence domain separator;
- evidence schema version;
- producer identity;
- transition identity;
- response identity or an explicit no-response marker;
- validation outcome;
- terminal disposition;
- finalized-state determination;
- protocol-payload hash or an explicit no-payload marker; and
- canonical provenance.

The attempt timestamp is evidence but is excluded from deterministic identity.
Canonical encoding must be versioned and byte-stable.

## 12.5 Append ordering

The logical append order within one observation cycle is:

1. durable successor snapshot;
2. immutable transition evidence;
3. the bounded predecessor observation, when eligible;
4. durable finalized outcome payload, when explicitly finalized and valid; and
5. immutable post-transition evidence containing the truthful terminal
   disposition.

`finalized_persisted` may be recorded only after the finalized outcome payload
has completed the existing durable persistence path. A persistence failure
therefore records `operational_failure` when evidence recording remains
available; it never records `finalized_persisted`.

This ordering is observation chronology. It does not backdate the predecessor
payload, insert it into the current-round snapshot stream, or change replay
chronology.

## 12.6 Separation from current-round observations

Post-transition evidence shall never be represented as a contemporaneous
current-round observation. It may contain outcome facts for predecessor Round
`R`, but it may not supply Board, Treasury, or decision-time Round state for
`R` or `R + 1`.

Consequently:

- replay ordering remains unchanged;
- Strategy never observes finalized state before evaluation;
- DecisionContext remains unchanged;
- replay semantics remain unchanged; and
- RFC-011 continues to distinguish observed and enriched outcome provenance.

---

# 13. Dataset Builder Consumption Boundary

RFC-012 does not redesign the Dataset Builder. It defines one narrow additional
input boundary for outcome assembly.

When RFC-012 evidence is present, the Dataset Builder shall evaluate it through
this boundary after it has frozen the ordered decision-time snapshots for the
predecessor lifecycle. It joins the evidence to exactly one predecessor
lifecycle using the complete canonical predecessor identity, not timestamp
proximity, file ordering, or the successor Round identifier alone.

The evidence may become the predecessor's finalized outcome only when:

1. its evidence and transition identities validate;
2. the context predicate in Section 10 passes;
3. its terminal disposition is `finalized_persisted`;
4. its payload is explicitly finalized under the existing predicate;
5. its raw payload hash, decoded payload, protocol revision, and canonical
   predecessor identity agree; and
6. no conflicting finalized outcome exists.

When accepted, the Builder copies only finalized outcome fields into the
existing outcome/evaluation position for Round `R`. It shall not:

- add the evidence to the replay snapshot sequence;
- create a new decision observation;
- alter snapshot timestamps or ordering;
- modify Board or Treasury history;
- expose the evidence through `DecisionContext`; or
- make the outcome visible before RFC-010's outcome-revelation boundary.

If current-round observed evidence and post-transition evidence both exist and
their canonical finalized-payload hashes agree, the current-round evidence
remains the canonical dataset source and the post-transition record remains
additional audit evidence. If they conflict, dataset construction fails closed.
If post-transition observed evidence conflicts with enrichment, dataset
construction also fails closed; enrichment never overwrites a local explicit
protocol observation.

This is an outcome-source extension, not a replay or dataset redesign.

## 13.1 Canonical provenance mapping

The existing broad outcome-source vocabulary remains unchanged:

- a valid post-transition predecessor outcome has
  `finalized_outcome_source = observed`;
- an outcome obtained only through historical enrichment has
  `finalized_outcome_source = enriched`; and
- a missing outcome has no outcome source.

Every locally observed outcome also has one immutable capture mode:

- `current_round` for an outcome obtained from the normal Board-selected
  snapshot stream; or
- `post_transition_predecessor` for an outcome obtained only through the
  RFC-012 evidence boundary.

Post-transition predecessor evidence is never classified as `enriched`.
Enriched evidence is never relabeled as locally observed. When agreeing
current-round and post-transition evidence both exist, `current_round` is the
canonical capture mode and the supplementary evidence remains independently
auditable by its evidence identity.

---

# 14. Terminal Dispositions

Every verified transition candidate reaches exactly one terminal disposition.

RFC-012 never leaves the outcome of a supplementary observation undefined.

The permitted terminal dispositions are:

| Disposition | Meaning |
|-------------|---------|
| `already_durable` | Finalized evidence already exists locally. No additional observation is required. |
| `finalized_persisted` | Explicit finalized protocol state was observed, validated, and durably persisted. |
| `not_finalized` | The predecessor was successfully observed but explicit finalized state was absent. |
| `account_unavailable` | The canonical predecessor account could not be observed. |
| `context_unproven` | The predecessor response could not be proven to originate from the required protocol context. |
| `invalid_or_ambiguous` | Identity, ownership, schema, or decoded protocol state failed validation. |
| `operational_failure` | Observation or persistence failed operationally after the successor snapshot had already been accepted. |

Every disposition is immutable.

Every disposition becomes append-only evidence.

No disposition permits inference of finalized protocol state.

---

# 15. Duplicate Prevention

RFC-012 preserves the existing exactly-once finalized persistence guarantee.

Duplicate prevention occurs at two boundaries.

First, before issuing a supplementary observation, the Observer determines
whether durable finalized evidence already exists.

If it does, no additional observation occurs.

Second, immediately before persistence, the existing finalized persistence
path performs canonical duplicate validation.

Consequently:

- finalized evidence is never overwritten;
- finalized evidence is never merged;
- finalized evidence is never replaced;
- duplicate finalized persistence remains impossible across process restart.

RFC-012 therefore extends the observation path without modifying finalized
identity semantics.

---

# 16. Determinism

RFC-012 preserves deterministic Observer behavior.

Given the same:

- Board observations;
- transition sequence;
- protocol responses;
- durable history;
- configuration;
- and validation rules;

the Observer shall make identical decisions regarding:

- transition eligibility;
- predecessor identity;
- observation budget;
- validation outcome;
- terminal disposition;
- finalized persistence; and
- append ordering.

RFC-012 introduces no:

- random timing;
- adaptive polling;
- retry-based acquisition;
- heuristic selection;
- probabilistic inference; or
- implementation-dependent behavior.

Live protocol observations remain time-dependent.

RFC-012 requires deterministic behavior only for the observations actually
obtained.

---

# 17. Append Ordering

RFC-012 preserves the existing append-only current-round observation stream.
The complete logical ordering for RFC-012 evidence is defined normatively in
Section 12.5.

That ordering reflects observation chronology rather than protocol chronology.

RFC-012 never:

- backdates predecessor evidence;
- inserts predecessor evidence into earlier replay ordering;
- rewrites existing observations; or
- alters DecisionContext chronology.

Current-round observations and post-transition predecessor observations remain
distinct evidence classes throughout Dataset Builder consumption and replay.

---

# 18. Failure Semantics

RFC-012 fails closed whenever:

- transition identity is invalid;
- predecessor identity is ambiguous;
- canonical PDA derivation fails;
- response context cannot be validated;
- explicit finalized state is absent;
- duplicate identity is ambiguous;
- decoded protocol state is invalid;
- persistence cannot complete.

Fail-closed means:

- no finalized outcome is inferred;
- no replay state is modified;
- no strategy input changes;
- no economic state changes;
- no retry authority is introduced; and
- no existing evidence is altered.

Importantly, supplementary observation failure never invalidates the already
accepted successor observation.

The primary Observer loop therefore continues normally even when the
supplementary observation fails.

---

# 19. Relationship to Existing RFCs

RFC-012 extends the Observer only.

## 19.1 RFC-008

RFC-008 remains the authoritative production outcome-acquisition system.

RFC-012 introduces no queueing, retry, restart recovery, production authority,
or production ledger behavior.

## 19.2 RFC-009

RFC-009 governance remains unchanged.

RFC-012 creates no continuation authority, approval authority, or release
authority.

## 19.3 RFC-010

RFC-010 replay semantics remain unchanged.

Post-transition predecessor observations remain future information relative to
their corresponding decision and therefore never enter:

- DecisionContext;
- Strategy;
- Ranked Candidate generation;
- Deployment Models; or
- evaluation inputs prior to outcome revelation.

## 19.4 RFC-011

RFC-011 Economics remains unchanged.

RFC-012 supplies additional observed outcome evidence.

It does not:

- settle protocol outcomes;
- calculate rewards;
- update participant state;
- calculate economic metrics; or
- modify Economic Simulation Records.

---

# 20. Repository and Governance Boundaries

The RFC document itself belongs to the Documentation Domain and grants no
operational authority.

Implementation artifacts are classified by authority and transitive
reachability under Repository Architecture, not by an RFC label, directory, or
the fact that RPC access is read-only.

An implementation that is isolated to passive research collection and
append-only research evidence remains in the Research Domain. That isolation
must be demonstrated by repository reachability validation.

If implementation modifies a shared dependency transitively reachable from a
production entry point, the affected artifact belongs to the Production
Release Closure and requires RFC-008 validation and approval. RFC-012 grants no
exception. Research evidence can enter Production only through the existing
Promotion Domain and separately approved governance.

RFC-012 introduces no wallet, signer, transaction, mining, claim, deployment,
production authorization, or production ledger capability.

---

# 21. Security Invariants

RFC-012 preserves every security and architectural invariant established by
earlier RFCs.

Specifically it preserves:

- passive observation;
- read-only protocol interaction;
- explicit protocol observation;
- append-only persistence;
- deterministic replay;
- provenance separation;
- fail-closed validation;
- exactly-once finalized persistence;
- duplicate prevention;
- reachability-based domain isolation;
- Promotion Domain governance; and
- the absence of production authority.

RFC-012 increases observation opportunity without increasing operational
authority.

---

# 22. Observability

RFC-012 shall expose sufficient immutable evidence to evaluate its own
effectiveness.

At minimum, the Observer shall report:

- contiguous transitions detected;
- transitions skipped;
- supplementary observations attempted;
- supplementary observations suppressed because finalized evidence already
  existed;
- finalized predecessor observations persisted;
- valid non-final predecessor observations;
- unavailable predecessor accounts;
- context validation failures;
- identity validation failures;
- operational observation failures;
- duplicate finalized observations prevented;
- transition-to-observation latency; and
- transition outcome distributions.

Every aggregate shall remain reproducible from immutable append-only evidence.

No metric may infer protocol-finalized state that was not explicitly observed.

---

# 23. Validation Requirements

An implementation of RFC-012 shall demonstrate:

1. successor observations are always persisted before supplementary work;
2. exactly one logical supplementary observation occurs for each read-eligible
   transition candidate;
3. no supplementary observation occurs for initial, unchanged, regressed,
   skipped, ambiguous, or already-finalized transitions;
4. predecessor identity is derived canonically;
5. every element of the Section 10 context predicate is enforced, including
   rejection of missing, older, mismatched-network, mismatched-provider, and
   weaker-commitment contexts;
6. finalized predecessor observations enter the existing durable persistence
   path;
7. explicit non-final predecessor observations never become finalized
   outcomes;
8. every terminal disposition remains explicit and deterministic;
9. duplicate finalized persistence remains impossible across repeated
   observations and process restart;
10. supplementary observation failure never invalidates the accepted successor
    observation;
11. transition, response, evidence, payload, producer, and schema identities
    reconstruct deterministically from canonical inputs;
12. `finalized_persisted` is emitted only after durable finalized persistence
    succeeds;
13. the Dataset Builder joins accepted evidence only by canonical predecessor
    identity and only after decision-time snapshots are frozen;
14. post-transition evidence never enters the replay snapshot sequence,
    `DecisionContext`, or Strategy input;
15. agreeing duplicate evidence resolves deterministically and conflicting
    observed or enriched outcomes fail closed;
16. canonical `observed`, `enriched`, `current_round`, and
    `post_transition_predecessor` provenance mapping is preserved;
17. replay ordering remains unchanged;
18. RFC-010 replay and future-information tests remain unchanged and pass;
19. RFC-011 provenance and missing-outcome tests remain unchanged and pass;
20. repository reachability classification is enforced and RFC-008 governance
    validation remains unchanged whenever applicable; and
21. no production capability becomes reachable.

Validation shall include deterministic fixtures for:

- finalized predecessor observations;
- already-durable predecessors;
- valid non-final predecessors;
- unavailable predecessors;
- context validation failures;
- network, provider, commitment, and response-slot mismatches;
- identity failures;
- malformed protocol responses;
- duplicate history;
- agreeing and conflicting current-round, post-transition, and enriched
  outcomes;
- deterministic identity reconstruction;
- outcome-only Dataset Builder consumption;
- DecisionContext and replay-snapshot exclusion;
- process restart;
- append failures; and
- successor observation preservation.

---

# 24. Completion and Effectiveness

## 24.1 Architectural completion

RFC-012 implementation is architecturally complete when:

1. every verified contiguous transition candidate receives exactly one bounded
   branch evaluation;
2. every read-eligible candidate receives exactly one supplementary observation
   opportunity and every already-durable candidate receives zero;
3. every completed branch produces exactly one immutable terminal disposition;
4. explicit finalized predecessor observations are durably persisted through
   the existing finalized persistence path before `finalized_persisted` is
   recorded;
5. the immutable evidence interface, identities, context predicate, append
   ordering, and canonical provenance rules validate deterministically;
6. the Dataset Builder consumes accepted evidence only as a predecessor outcome
   after freezing decision-time observations;
7. duplicate finalized observations remain impossible;
8. replay ordering, `DecisionContext`, and Strategy visibility remain unchanged;
9. RFC-008 through RFC-011 compatibility and repository governance checks pass;
   and
10. all Section 23 validation requirements pass.

Architectural completion does not depend on achieving a particular recovery
percentage. It is established by deterministic conformance to this contract.

## 24.2 Effectiveness measurement

Effectiveness is measured after architectural completion over an explicitly
identified, bounded observation window. The evidence report shall state:

- window identity and start/end boundaries;
- verified transition candidates;
- read-eligible candidates;
- already-durable candidates;
- supplementary observations attempted;
- post-transition finalized outcomes persisted;
- total locally observed finalized outcomes;
- outcomes still requiring enrichment;
- unresolved outcomes;
- attempt success rate; and
- each terminal-disposition rate.

The post-transition observed count is exactly the count of accepted outcomes
whose canonical capture mode is `post_transition_predecessor`. Enrichment
avoided is reported only when the same bounded dataset build would otherwise
have classified those outcomes as `enriched`; it is never inferred merely from
an RPC response.

The investigations establish an evidence-supported opportunity, not a realized
yield or defensible minimum percentage. Effectiveness results therefore inform
subsequent evaluation but do not retroactively determine whether the bounded
implementation conforms to RFC-012.

---

# 25. Explicitly Outside RFC-012

RFC-012 intentionally excludes:

## Replay

- replay ordering;
- replay visibility;
- DecisionContext construction;
- Dataset Builder behavior beyond the outcome-only evidence boundary in Section
  13;
- Dataset Management behavior;
- enrichment policy;
- historical repair; and
- replay reconstruction.

## Strategy

- strategies;
- deployment models;
- evaluation;
- experiment execution;
- metrics;
- experiment registries; and
- research conclusions.

## Economics

- settlement;
- participant state;
- economic scenarios;
- economic metrics;
- economic simulation;
- Economic Simulation Records; and
- protocol valuation.

## Production

- production collection;
- production outcome acquisition;
- continuation authority;
- production governance;
- production recovery;
- wallet operations;
- signer operations;
- transaction construction;
- transaction submission;
- mining; and
- claims.

## Observer Enhancements

RFC-012 also excludes:

- poll interval changes;
- repeated predecessor polling;
- background observation queues;
- websocket subscriptions;
- protocol event subscriptions;
- concurrent observation;
- multi-provider observation;
- transition prediction; and
- historical backfill.

Those remain future research topics.

---

# 26. Remaining Research Questions

RFC-012 intentionally leaves two questions unanswered:

1. What percentage of currently enriched outcomes become locally observed after
   implementation?

2. What percentage improvement constitutes a materially successful
   architectural enhancement?

Those questions require implementation evidence.

RFC-012 deliberately avoids inventing thresholds unsupported by current
research.

---

# 27. Architectural Summary

RFC-012 introduces one bounded architectural enhancement.

```
Current Observation

        ↓

Persist Successor Snapshot

        ↓

Detect Contiguous Transition

        ↓

One Context-Bound Predecessor Observation

        ↓

Durable Finalized Evidence When Valid

        ↓

Explicit Terminal Disposition

        ↓

Continue Normal Observation
```

The enhancement preserves:

- the existing Observer architecture;
- deterministic replay;
- append-only evidence;
- durable finalized persistence;
- provenance separation;
- fail-closed validation;
- reachability-based repository-domain isolation; and
- every architectural invariant established by RFC-008 through RFC-011.

RFC-012 does not redesign the Observer.

It introduces one bounded, deterministic opportunity to observe
protocol-finalized state that the existing Observer architecture intentionally
never attempts.

It does not infer protocol state.

It does not reinterpret protocol state.

It does not reconstruct protocol state.

Every accepted finalized outcome continues to originate from an explicit
protocol observation.

The enhancement is therefore observational rather than inferential.

Its sole purpose is to increase the probability of capturing protocol-finalized
state while preserving deterministic replay, append-only evidence,
provenance separation, and every architectural invariant established by
RFC-008 through RFC-011.

That single architectural enhancement is the entirety of RFC-012.
