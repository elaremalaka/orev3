# RFC-014 — Protocol Revision Provenance

**Status:** Draft for architectural review

**Scope:** Immutable provenance for multiple official ORE protocol revisions

**Implementation authorized:** No

---

# 1. Overview

RFC-014 defines how ORE Miner V3 represents, validates, propagates, and
consumes multiple official ORE protocol revisions.

Protocol revision becomes first-class immutable provenance. It identifies the
protocol semantics governing an observation or replay round, supplies audit
and validation authority, and binds revision-dependent economic behavior. It
does not become decision-time information or a predictive signal.

RFC-014 introduces only the provenance contracts required to connect existing
architectural boundaries:

```text
Official Protocol Revision

        +

Authoritative Activation Binding

        ↓

Observer Provenance

        ↓

RFC-012 Evidence Provenance

        ↓

Dataset Revision Manifest

        ↓

Replay Validation and Research Controls

        ↓

Revision-Matched RFC-011 Economics
```

The preserved decision path remains:

```text
Replay

↓

DecisionContext

↓

Strategy

↓

Deployment

↓

Evaluation
```

Protocol revision is validated around this path. It never enters
`DecisionContext`, feature computation, Strategy, or ranking.

---

# 2. Motivation

ORE Miner V3 Version 1.0 is pinned to official ORE source revision:

`3112ab78a64f92892a70d5d4cbd17e1d14b1c2fe`

The completed Protocol Change Impact Assessment established that a later
official revision changed SOL settlement from parimutuel redistribution to
principal return with administrative and losing-square protocol fees. It also
changed the meaning of a serialized Round `u64` from `total_winnings` to
`total_returned_sol` without changing the field's width or position.

The change demonstrates that:

- byte-compatible account layouts may have incompatible semantics;
- an existing field name may cease to describe the bytes it contains;
- a cumulative dataset may span distinct economic regimes;
- an official source commit does not, by itself, prove when a deployed network
  began executing that source; and
- protocol revision must be known before revision-sensitive facts are decoded,
  joined, replayed, researched, or settled economically.

The existing architecture already isolates Strategy, outcome evidence, and
economics correctly. What is missing is one canonical, immutable provenance
contract connecting those boundaries.

---

# 3. Problem Statement

The repository currently carries protocol revision at selected boundaries:

- RFC-012 canonical evidence binds the pinned protocol and decoder; and
- RFC-011 Economic Scenario selects one protocol revision and fails closed on
  mismatch.

Normal Observer snapshots and managed replay datasets do not consistently
carry an immutable round-level statement proving:

1. which official protocol semantics governed the observed round;
2. which deployed program activation made those semantics applicable;
3. which decoder interpreted the account bytes;
4. whether normal observations and finalized outcome evidence agree; and
5. whether a consumer supports that revision.

Without this contract, a consumer can parse valid bytes under the wrong
semantic meaning while preserving deterministic but incorrect results.
Dataset version, Replay version, timestamps, filenames, and current source
state are not substitutes for protocol provenance.

---

# 4. Goals

RFC-014 shall:

- define one canonical immutable Protocol Revision Identity;
- keep that identity stable across compatible decoder implementation changes;
- distinguish source semantics from on-chain activation authority;
- distinguish governing protocol context from observation/read context;
- establish one authority for decoder compatibility and cross-revision
  semantic compatibility declarations;
- define an immutable Activation Binding for each governed network interval;
- bind accepted Observer facts to one revision, activation, and decoder;
- preserve revision identity in RFC-012 transition and outcome evidence;
- make revision coverage part of deterministic dataset provenance;
- require revision agreement before lifecycle or outcome reconciliation;
- define fail-closed rules for ambiguous, conflicting, and unsupported
  revisions;
- allow cumulative datasets to preserve multiple revisions without silently
  pooling their semantics;
- preserve RFC-010 replay and decision-time purity;
- preserve RFC-011's ownership of protocol-specific economics;
- preserve RFC-012's outcome-only evidence boundary;
- make protocol revision an RQ-003 audit and population-control variable;
- preserve immutable historical artifacts and deterministic reconstruction;
- distinguish legacy reproducibility from RFC-014-aware replay eligibility;
  and
- support explicit research comparison between official revisions.

---

# 5. Non-Goals

RFC-014 does not:

- redesign the Observer polling loop;
- define a new account decoder;
- define any official ORE protocol revision's settlement arithmetic;
- redesign the Dataset Builder;
- redesign Replay or `DecisionContext`;
- modify Strategy or Deployment Model interfaces;
- redesign RFC-011 Economics;
- redesign RFC-012 evidence capture;
- revise the RQ-003 research question;
- declare any protocol revision predictive;
- define a model, feature, Strategy, or ranking procedure;
- identify the current on-chain activation boundary without authoritative
  evidence;
- infer a deployed revision from Git merge time;
- infer revision from observed field values;
- normalize semantically different fields into one unqualified meaning;
- provide live mining, transaction, wallet, or deployment capability;
- rewrite an existing dataset or experiment;
- change RFC-008 or RFC-009 governance; or
- authorize implementation or production operation.

---

# 6. Current Architecture

## 6.1 RFC-010

[RFC-010](../docs/rfcs/RFC-010-STRATEGY-LAB.md) requires deterministic Replay,
immutable experiments, versioned datasets and components, pure Strategies, and
no future-information leakage.

The Historical Dataset supplies ordered observations and outcomes. Replay
constructs immutable `DecisionContext` objects. Strategy expresses preference,
Deployment expresses conviction, and Evaluator reveals the historical outcome.

RFC-010 does not define protocol revision provenance.

## 6.2 RFC-011

[RFC-011](../docs/rfcs/RFC-011-ORE-DEPLOYMENT-ECONOMICS.md) already treats
protocol revision as immutable Economic Scenario authority. Protocol facts,
constraints, transaction assumptions, settlement arithmetic, and resulting
records are revision-bound. A revision mismatch fails closed.

RFC-011 correctly isolates the economic change. It depends on upstream replay
facts whose governing revision must be equally authoritative.

## 6.3 RFC-012

[RFC-012](../docs/rfcs/RFC-012-OBSERVER-FINALIZATION-CAPTURE.md) binds its
canonical predecessor and response identities to the pinned ORE program,
protocol revision, and decoder. It preserves post-transition evidence outside
normal replay snapshots and exposes accepted evidence only at the outcome
boundary.

RFC-012's identity model is revision-aware but currently assumes one pinned
revision.

## 6.4 RQ-003

[RQ-003](../docs/research/questions/RQ-003-winning-square-predictability.md)
requires immutable dataset identity, chronology, lifecycle and cadence
controls, outcome provenance, and a strict decision-time freeze. It prohibits
outcome evidence, capture metadata, chronology proxies, and future information
from predictive inputs.

RQ-003 does not yet require protocol revision as an explicit population and
compatibility control.

## 6.5 Missing end-to-end provenance

The current boundaries protect future-information isolation and economic
revision matching locally. They do not yet provide one end-to-end proof that
the revision assigned at observation remains unchanged through dataset
construction, replay eligibility, research evaluation, and RFC-011 settlement.

---

# 7. Proposed Architecture

RFC-014 introduces four immutable provenance concepts:

1. **Protocol Revision Identity** — the exact official source semantics and
   supported decoding contract.
2. **Activation Binding** — authoritative evidence that places one revision on
   one network and governed interval.
3. **Observation Revision Provenance** — the revision, activation, decoder, and
   raw observation relationship accepted for one protocol observation.
4. **Dataset Revision Manifest** — the ordered, deterministic assignment of
   replay rounds to revision-homogeneous segments, including ambiguous and
   unsupported dispositions.

Two immutable authority bindings support those concepts without becoming
protocol revisions themselves:

1. **Decoder Compatibility Binding** — approval for one concrete decoder
   implementation to interpret one Protocol Revision Identity under that
   revision's decoder contract.
2. **Semantic Compatibility Declaration** — approval for one exact protocol
   fact to be treated as semantically equivalent across named revisions and
   within a declared scope.

The Protocol Provenance Authority defined in Section 9.4 is the sole owner of
those bindings. Dataset and consumer components reference them; they never
create or redefine them.

These concepts form a provenance plane beside the existing replay plane:

```text
Provenance plane

Revision Identity ── Activation Binding ── Observation Provenance
                                              │
                                              ▼
                                     Dataset Revision Manifest
                                              │
                          ┌───────────────────┴───────────────────┐
                          ▼                                       ▼
                Replay eligibility                      RFC-011 matching

Decision plane

Normal observations ── Replay ── DecisionContext ── Strategy ── Deployment

Outcome plane

Finalized outcome ── Evaluation ── RFC-011 settlement
```

The provenance plane validates and selects eligible artifacts. It does not add
fields to `DecisionContext` or alter the decision and outcome planes.

## 7.1 Ownership

- Protocol Revision Identity owns source-semantic and decoder-contract
  identity, but not concrete decoder implementation identity.
- Protocol Provenance Authority owns acceptance of Protocol Revision
  Identities, Activation Bindings, Decoder Compatibility Bindings, and Semantic
  Compatibility Declarations.
- Activation Binding owns applicability to a deployed network interval.
- Observer owns truthful capture of revision provenance for accepted protocol
  observations.
- RFC-012 owns revision-bound supplementary evidence identity.
- Dataset Builder owns revision-consistent assembly and the Dataset Revision
  Manifest. It consumes approved semantic compatibility declarations.
- Replay owns consumer compatibility validation before constructing a
  `DecisionContext`.
- RFC-011 owns revision-specific economic interpretation.
- RQ-003 owns revision-aware research population and reporting rules.
- Strategy owns none of these responsibilities.

---

# 8. Architectural Invariants

RFC-014 shall preserve:

- exactly one semantic revision for every interpreted protocol observation;
- exactly one activation binding for every known revision assignment;
- exactly one revision disposition for every replay round;
- immutable, deterministic provenance identities;
- every concrete decoder bound through one approved Decoder Compatibility
  Binding without changing Protocol Revision Identity;
- no inference from filenames, timestamps, values, or current source state;
- no assumption that byte compatibility means semantic compatibility;
- agreement between normal observations and outcome evidence joined into one
  replay round;
- one authoritative owner for every accepted cross-revision semantic
  compatibility declaration;
- immutable and append-only raw observations and RFC-012 evidence;
- immutable historical datasets, experiments, and economic records;
- successor artifacts rather than rewritten history;
- deterministic reconstruction from the same authoritative inputs;
- explicit ambiguity and unsupported-revision dispositions;
- fail-closed interpretation when provenance is absent, ambiguous, or
  conflicting;
- RFC-010 decision-time purity;
- RFC-011 protocol-versioned settlement;
- RFC-012 outcome-only evidence consumption;
- RQ-003 chronology and future-information controls;
- revision exclusion from `DecisionContext`, features, Strategy, and ranking;
  and
- no production authority created by provenance metadata.

---

# 9. Protocol Revision Identity

## 9.1 Definition

A Protocol Revision Identity is the immutable identity of one supported set of
official ORE protocol semantics.

It shall bind at minimum:

- identity schema and version;
- official protocol source repository identity;
- exact official source revision;
- ORE program identity;
- account-schema identity;
- instruction-contract identity;
- protocol-semantic contract identity;
- decoder-contract identity;
- predecessor Protocol Revision Identity, when one exists; and
- deterministic identity digest.

The source revision identifies semantics. Marketing labels such as “V4” are
descriptive metadata only and cannot replace the exact source revision.

## 9.2 Canonical identity

Protocol Revision Identity shall be reconstructed from a versioned canonical
encoding of its immutable fields. Field order, string encoding, absent-value
representation, and digest algorithm shall be fixed by the identity schema.

The identity must change when any semantic, account, instruction, program, or
decoder-contract binding changes.

The identity does not change when a new concrete decoder implementation is
approved for the same decoder contract. Concrete decoder implementations are
bound separately through Decoder Compatibility Bindings.

Two revisions may share account size or instruction bytes without sharing an
identity. Semantic equivalence must be proven explicitly for each fact a
consumer intends to treat as common.

## 9.3 Revision chain

Supported official revisions shall form an ordered, auditable lineage. A
successor identifies its immediate supported predecessor when one exists.

Source lineage does not prove activation. A revision may be officially merged
but never govern the observed network. Such a revision remains visible in
source audit history but has no governing Activation Binding for that network.

## 9.4 Protocol Provenance Authority

RFC-014 establishes one Protocol Provenance Authority as the architectural
owner of accepted protocol-provenance assertions.

The authority accepts, through explicit human review under existing repository
governance:

- Protocol Revision Identities;
- Activation Bindings;
- Decoder Compatibility Bindings; and
- Semantic Compatibility Declarations.

Acceptance binds the exact immutable artifact and its deterministic identity.
An unaccepted draft, source commit, announcement, decoder, or compatibility
claim carries no RFC-014 authority. Acceptance creates no production, release,
wallet, transaction, or deployment authority.

A Decoder Compatibility Binding shall identify:

- one Protocol Revision Identity;
- that revision's decoder-contract identity;
- one concrete decoder implementation identity;
- the account and field scope it may decode;
- validation and review evidence; and
- a deterministic binding identity.

Adding, replacing, or withdrawing support for a concrete decoder creates a new
binding history. It never changes the official Protocol Revision Identity or a
historical Observation Revision Provenance identity.

A Semantic Compatibility Declaration shall identify:

- the exact named Protocol Revision Identities being compared;
- the exact fact and semantic identity in each revision;
- the scope in which equivalence is asserted;
- any exclusions or preconditions;
- supporting evidence and explicit human approval; and
- a deterministic declaration identity.

The Protocol Provenance Authority is the sole issuer of accepted Semantic
Compatibility Declarations. Dataset Builder, Replay, RQ-003, RFC-011, and other
consumers may narrow their own eligibility but may not broaden, replace, or
redefine an accepted declaration. Absence of a declaration means equivalence
has not been established.

---

# 10. Activation Binding

## 10.1 Definition

An Activation Binding is immutable evidence that one Protocol Revision
Identity governed one specified network interval.

It shall bind at minimum:

- activation-binding schema and version;
- Protocol Revision Identity;
- network identity and expected genesis hash;
- deployed ORE program and executable identity;
- authoritative deployment or upgrade evidence identity;
- evidence linking that executable to the claimed official source revision;
- the canonical activation boundary supported by that evidence;
- predecessor Activation Binding, when one exists;
- human review or governance evidence required to accept the binding; and
- deterministic binding identity.

## 10.2 Authority

Official source history establishes what a revision means. Authoritative
on-chain deployment evidence or an equivalent official activation record
establishes where and when it governed.

An Activation Binding becomes eligible only after the Protocol Provenance
Authority accepts its exact content and supporting evidence. A program address
alone is insufficient when the program is upgradeable; the binding must
identify the deployed executable or equivalent immutable deployment evidence
and its reviewed relationship to the official source revision.

The following are insufficient by themselves:

- Git author, commit, merge, or release timestamp;
- an announcement timestamp;
- local observer restart time;
- first observed changed field value;
- a filename or collector-session boundary; or
- the current default branch.

## 10.3 Interval rules

Known Activation Bindings for one network shall be ordered and non-overlapping.
A governed instant may resolve to at most one revision.

Each binding shall declare one canonical boundary domain and inclusive or
exclusive boundary rule so that identical evidence resolves identical protocol
contexts. Implementations may not substitute wall-clock time for a slot,
instruction, deployment, or other boundary established by the accepted
evidence.

The architecture does not require a fabricated continuous history. If
activation evidence leaves a gap, the affected interval is revision-ambiguous.
If two accepted bindings overlap, validation fails closed until the conflict is
resolved by authoritative evidence.

If activation occurs near or during a round, that round may be assigned only
when authoritative evidence defines which deployed semantics governed the
relevant observations and finalization. Board advancement alone is not
activation evidence.

## 10.4 Immutability

An accepted Activation Binding is never edited to move a boundary. New evidence
creates a successor binding or successor provenance artifact. Historical
artifacts derived under an earlier binding retain their original identities.

---

# 11. Observation Provenance

## 11.1 Accepted observations

Every semantically accepted Board, Treasury, Round, or related protocol
observation shall preserve:

- network and genesis identity;
- ORE program identity;
- Protocol Revision Identity;
- Activation Binding identity;
- decoder identity;
- Decoder Compatibility Binding identity;
- account identity and owner;
- governing protocol context;
- observation/read context and commitment already required by the observation
  path;
- raw payload identity; and
- deterministic Observation Revision Provenance identity.

The two contexts are distinct:

- **Governing protocol context** is the immutable protocol execution context
  that created, finalized, or last authoritatively assigned semantic meaning to
  the fact being interpreted.
- **Observation/read context** is the response context at which the Observer
  retrieved the account bytes.

The revision shall be resolved from the Activation Binding applicable to the
governing protocol context. The read context proves when and under what
commitment the bytes were obtained; it does not, by itself, establish which
revision gave retained account state its meaning.

A current response may expose an account whose relevant state was produced
under an earlier revision. Conversely, one account may contain facts affected
by more than one revision. If the governing context for every required fact
cannot be established under one revision, the observation is
revision-ambiguous. A Semantic Compatibility Declaration may allow a consumer
to compare separately revision-bound facts; it does not relabel an ambiguous
observation as known.

Neither governing context nor revision shall be inferred from decoded values,
wall-clock proximity, or the current active program alone.

## 11.2 Decoder binding

A decoder may interpret an observation only when one accepted Decoder
Compatibility Binding connects its concrete identity and scope to the resolved
Protocol Revision Identity and decoder contract. A structurally parseable
payload is not accepted under a decoder bound to different semantics.

Raw account bytes remain authoritative evidence. Decoded fields are
revision-bound interpretations of those bytes.

## 11.3 Unsupported and ambiguous observations

An unsupported or ambiguous revision produces no semantically accepted decoded
observation. The Observer shall not relabel the bytes as the previously pinned
revision.

RFC-014 does not define whether an implementation retains raw diagnostic bytes
for such an observation. Any retention must remain truthful, append-only, and
clearly outside accepted replay input.

## 11.4 Existing behavior

Revision provenance does not alter:

- polling cadence;
- Board-selected current-round observation;
- persistence ordering;
- duplicate detection;
- finalized-state detection within a supported revision;
- restart behavior; or
- the passive nature of the Observer.

---

# 12. RFC-012 Evidence Provenance

RFC-012's immutable evidence interfaces remain authoritative.

RFC-014 generalizes their pinned revision relationship as follows:

- canonical predecessor identity binds the predecessor's Protocol Revision
  Identity and Activation Binding;
- preserved protocol payload binds the Decoder Compatibility Binding approved
  for that revision;
- response identity includes those revision and activation identities;
- transition evidence preserves the successor snapshot's independent
  Observation Revision Provenance identity; and
- post-transition evidence remains outcome-only.

## 12.1 Same-revision transition

For an ordinary `R → R + 1` transition within one activation interval,
predecessor and successor provenance shall resolve to the same revision and
binding.

## 12.2 Cross-revision transition

A predecessor and successor may resolve to different revisions only when an
authoritative Activation Binding places the activation between their governed
protocol contexts.

The successor Board response proves the observed round transition. It does not
prove the protocol activation or infer the predecessor revision. Each side
must resolve through authoritative activation provenance.

The predecessor response context remains the RFC-012 read context used to
prove the bounded observation followed the accepted Board response. It does
not replace the predecessor's governing protocol context. A predecessor read
performed after activation may therefore retain the predecessor's earlier
revision only when authoritative activation and governing-context evidence
prove that relationship.

If the predecessor revision, successor revision, or boundary relationship is
ambiguous, RFC-012 evidence cannot become an accepted finalized outcome.

## 12.3 Preserved boundary

RFC-014 does not change:

- RFC-012's zero-or-one predecessor read;
- context acceptance predicate;
- terminal dispositions;
- durable append ordering;
- duplicate protection;
- canonical capture-mode mapping; or
- exclusion of RFC-012 evidence from replay snapshots and `DecisionContext`.

---

# 13. Dataset Provenance

## 13.1 Dataset Revision Manifest

Every multi-revision-capable dataset shall carry an immutable Dataset Revision
Manifest.

The manifest shall preserve:

- manifest schema and version;
- dataset identity;
- ordered Protocol Revision Identities;
- ordered Activation Binding identities;
- Decoder Compatibility Binding identities;
- deterministic revision-homogeneous segment boundaries;
- round-to-segment assignments;
- revision-ambiguous and revision-unsupported round dispositions;
- revision-specific field-semantic declarations;
- references to accepted Semantic Compatibility Declarations for proven shared
  facts; and
- deterministic manifest identity.

The manifest participates in dataset identity. Changing one assignment,
boundary, decoder binding, semantic declaration, or referenced compatibility
declaration produces a new dataset identity.

## 13.2 Round consistency

Every replay round must have exactly one revision disposition:

- known and supported;
- revision-ambiguous; or
- revision-unsupported.

A known replay round requires revision agreement across:

- every accepted normal snapshot in the lifecycle;
- the selected decision snapshot;
- current-round finalized evidence, when present;
- RFC-012 post-transition evidence, when present; and
- enriched outcome evidence, when present.

Conflicting evidence fails dataset construction. Enrichment never overrides a
locally observed revision or resolves an ambiguous activation by assumption.

## 13.3 Semantic preservation

Revision-specific fields remain revision-specific. A Dataset Builder may emit
a shared canonical fact only when equivalence across the named revisions is
established by an accepted Semantic Compatibility Declaration and the manifest
references that exact declaration identity.

The Dataset Builder does not author or expand semantic compatibility. It
validates and consumes declarations issued by the Protocol Provenance
Authority. Consumers may further restrict the declared scope but may not infer
additional equivalence.

Matching serialized offsets, numeric types, or event names do not establish
equivalence. The original raw field interpretation and revision provenance
must remain reconstructable.

## 13.4 Independent integrity dimensions

Dataset integrity, lifecycle completeness, outcome completeness, and revision
integrity are independent.

A round with complete observations and a finalized outcome may still be
ineligible because its governing revision is ambiguous or unsupported. A known
revision does not fabricate a missing outcome or repair an incomplete
lifecycle.

## 13.5 Freeze boundary

The Dataset Builder shall freeze ordered decision-time snapshots before
discovering or consuming RFC-012 evidence or enrichment, exactly as RFC-012
requires.

Revision provenance attached to a normal snapshot is audit metadata about the
semantics of that already-observed state. Outcome evidence may validate that
provenance but may not modify snapshot membership, ordering, values, or the
selected decision state.

---

# 14. Replay Responsibilities

Replay remains responsible for deterministic historical reconstruction.

RFC-014 distinguishes two replay purposes:

- **legacy reproduction** reconstructs an existing historical result under its
  original immutable dataset, software, and documented protocol assumptions;
  and
- **RFC-014-aware replay eligibility** determines whether an artifact may
  participate in a new replay, research claim, or economic simulation under
  RFC-014 provenance rules.

For an RFC-014-aware execution, before constructing a `DecisionContext`, Replay
validation shall establish:

- the replay round has known, supported revision provenance;
- the dataset manifest and round assignment identities validate;
- the Replay implementation supports the revision-neutral facts it consumes;
- revision-sensitive fields are either supported or excluded by an explicit
  eligibility rule backed, where equivalence is required, by an accepted
  Semantic Compatibility Declaration; and
- the experiment's immutable revision-eligibility policy admits the round.

Replay may load a cumulative mixed-revision dataset. It shall not silently
erase segment boundaries or interpret all rounds as one semantic regime.

Protocol Revision Identity and Activation Binding remain available to Replay
validation, experiment orchestration, audit reporting, and artifact identity.
They are not inserted into `DecisionContext`.

Replay ordering, decision-point selection, outcome revelation, and historical
state reconstruction remain unchanged.

Legacy reproduction does not become RFC-014-aware merely because it remains
readable and deterministically reproducible. It may reproduce the original
historical result and claims only. It may not support a new RFC-014-aware
experiment or a current protocol-compatibility claim until successor provenance
establishes eligibility under Section 19.

---

# 15. Strategy Responsibilities

Strategy responsibilities remain exactly those defined by RFC-010.

A Strategy:

- consumes immutable `DecisionContext`;
- produces a deterministic `RankedCandidateSet`;
- may update deterministic state only after outcome revelation; and
- remains independent of protocol provenance.

Protocol revision shall not be exposed to Strategy directly or indirectly
through:

- `DecisionContext`;
- a feature value;
- Strategy configuration intended as a signal;
- candidate metadata;
- explanation payload supplied by the framework;
- ranking tie-breaking; or
- dataset identity leakage.

Researchers may run the same Strategy separately on revision-specific
populations. Population selection belongs to experiment orchestration and
research protocol, not Strategy behavior.

---

# 16. RFC-011 Responsibilities

RFC-011 remains the sole owner of protocol-specific economic interpretation.

Every Economic Scenario continues to select exactly one Protocol Revision
Identity. Its Protocol Constraint Model, Transaction Model, Inclusion Model,
Settlement Model, and Economic Metrics must be approved and identity-bound for
that revision.

RFC-011 shall consume a replay round only when:

- the round has known revision provenance;
- the round's Protocol Revision Identity matches the Economic Scenario;
- all required revision-sensitive facts have compatible semantics;
- finalized outcome provenance is valid; and
- existing RFC-011 continuity and completeness rules pass.

A mixed-revision dataset shall be divided into revision-homogeneous economic
intervals. Each independently simulated interval requires an explicit
immutable initial Participant Economic State.

RFC-014 does not authorize automatic Participant Economic State transfer
across a protocol activation. Such transfer requires separately defined
transition semantics.

Historical RFC-011 simulations remain valid for the exact revision and dataset
identities they recorded.

---

# 17. RQ-003 Responsibilities

RQ-003 remains the governing protocol for decision-time winning-square
information research.

Protocol revision becomes a mandatory audit and population-control variable.
Every RQ-003 dataset and result shall report:

- revision identities and governed round ranges;
- activation-binding identities;
- known, ambiguous, unsupported, and excluded round counts;
- revision-specific lifecycle and outcome completeness;
- revision-specific cadence and capture-mode distributions; and
- the exact revision eligibility policy used.

Revision is prohibited as:

- a predictive feature;
- a feature dependency;
- a ranking input;
- a tie-breaker;
- a proxy derived from round identifier or timestamp; or
- a means of selecting favorable held-out outcomes.

Feature semantics must remain identical across every population in which one
feature identity is reused. A source field whose meaning changed across
revisions requires a different feature semantic identity or exclusion from the
cross-revision comparison.

RQ-003 may compare revisions explicitly. Such comparison shall:

- preserve chronology;
- use predeclared populations and eligibility rules;
- report each revision separately;
- preserve the same outcome-free decision boundary;
- distinguish within-revision evidence from cross-revision generalization;
  and
- avoid treating increased pooled sample size as evidence of semantic
  compatibility.

---

# 18. Mixed-Revision Dataset Rules

## 18.1 Physical coexistence

One physical dataset may contain multiple official revisions. It shall be
logically represented as an ordered set of immutable revision-homogeneous
segments.

Physical coexistence does not authorize semantic pooling.

## 18.2 Eligibility

Every consumer shall declare an immutable revision-eligibility policy.

The policy shall identify:

- supported Protocol Revision Identities;
- supported revision-neutral and revision-specific facts;
- accepted Semantic Compatibility Declaration identities required for any
  cross-revision equivalence;
- treatment of ambiguous and unsupported rounds;
- whether one revision or multiple revisions may be included; and
- required per-revision reporting.

Ambiguous and unsupported rounds remain auditable but are excluded from any
operation requiring interpreted protocol semantics. They shall not be assigned
to the nearest segment.

A consumer policy may narrow an accepted declaration's scope or reject a fact.
It may not author equivalence, broaden a declaration, or substitute its own
semantic compatibility claim.

## 18.3 Research pooling

A pooled research result across revisions is permitted only when:

- pooling is predeclared;
- the research estimand explicitly spans those revisions;
- feature and label semantics are compatible;
- revision-specific results are also reported;
- chronology and round grouping remain intact; and
- the pooled result is not represented as a within-revision result.

## 18.4 Economic execution

RFC-011 economic execution is never pooled across revisions within one
Economic Scenario. Revision-homogeneous intervals are simulated separately.

## 18.5 Boundary rounds

A round whose observations or finalization cross an activation boundary is
eligible only when authoritative activation evidence establishes one governing
semantic revision for every fact the consumer requires. Otherwise the round is
revision-ambiguous.

---

# 19. Migration Strategy

Migration is additive and immutable.

## 19.1 Existing artifacts

Existing raw observations, replay datasets, Discovery Sessions, RQ-003
documents, RFC-010 experiments, and RFC-011 Economic Simulation Records shall
not be rewritten.

Their historical claims remain bound to their existing artifact identities and
documented protocol assumptions.

Those artifacts retain **legacy reproducibility**: the ability to reconstruct
their original results with the original immutable inputs, component versions,
and protocol assumptions. Legacy reproduction preserves a historical claim; it
does not certify RFC-014 provenance and does not make the artifact eligible for
a new experiment, cross-revision comparison, or current economic simulation.

## 19.2 Legacy RFC-014-aware eligibility

A legacy immutable dataset may receive a successor provenance artifact that
binds its complete coverage to the Version 1.0 revision only when authoritative
activation evidence proves that every included round was governed by that
revision.

The successor provenance artifact does not change the original bytes or
identity. It records the relationship and produces a distinct migrated dataset
or manifest identity.

If complete coverage cannot be proven, affected rounds remain ambiguous.

Only the successor provenance artifact or migrated dataset identity may claim
RFC-014-aware replay eligibility. The original artifact remains reproducible
under its legacy contract but does not acquire new provenance retroactively.

## 19.3 New observations

Newly accepted observations shall carry revision provenance from collection.
They shall not depend on a later Dataset Builder to guess the active revision.

## 19.4 Immediate and long-term dataset forms

Revision-specific physical datasets are the safest initial form because they
minimize accidental semantic mixing.

An immutable composite Dataset Revision Manifest is the long-term cumulative
form. Both forms shall produce identical per-round revision assignments and
consumer eligibility results from identical authoritative inputs.

## 19.5 Discovery and research history

Discovery Sessions 1–4 remain unchanged. Later work may cite their proven
revision coverage or note ambiguity, but shall not retroactively modify their
observations or conclusions.

---

# 20. Compatibility Requirements

RFC-014 is compatible with existing architecture only when all of the
following hold:

- RFC-010 public interfaces remain unchanged;
- `DecisionContext` remains byte-equivalent for identical eligible historical
  facts;
- Strategy and Deployment Model behavior remain unchanged for identical
  contexts and configuration;
- Evaluator receives the same authoritative winning-square fact for a revision
  whose winner semantics are compatible;
- RFC-012 evidence remains outcome-only;
- RFC-012 current-round and post-transition capture modes retain their existing
  meanings;
- observed and enriched outcome provenance remains distinct;
- RFC-011 continues to select one exact revision per Economic Scenario;
- SOL and ORE remain separate native denominations;
- raw observation ordering and append-only history remain unchanged;
- old datasets and experiment records retain legacy reproducibility under their
  original contracts without thereby becoming RFC-014-aware eligible;
- migration produces successor identities rather than mutating prior
  identities;
- revision-aware reconstruction and legacy reproduction produce identical
  decision and result artifacts when an entire legacy artifact is
  authoritatively proven, migrated, and replayed under the same revision and
  component contracts; and
- no provenance artifact grants production, wallet, transaction, or deployment
  authority.

Compatibility must be proven independently for:

- account decoding;
- instruction semantics;
- replay facts;
- outcome facts;
- feature semantics;
- evaluation labels; and
- RFC-011 economics.

Compatibility in one category does not imply compatibility in another.

---

# 21. Failure Semantics

RFC-014 fails closed when:

- Protocol Revision Identity is missing, malformed, or unreconstructable;
- official source identity is ambiguous;
- Activation Binding is missing for a claimed known assignment;
- a claimed binding or declaration lacks Protocol Provenance Authority
  acceptance;
- activation evidence is invalid or unauthoritative;
- activation intervals overlap or conflict;
- a governing interval has an unresolved gap;
- a round crosses an unresolved activation boundary;
- no accepted Decoder Compatibility Binding covers the decoder, revision, and
  required scope;
- raw payload and decoded representation disagree;
- normal observations within one lifecycle disagree on revision;
- snapshot and outcome evidence disagree on revision;
- current-round, RFC-012, and enriched evidence conflict;
- a dataset manifest assignment cannot be reconstructed;
- a consumer does not support the round's revision;
- a required Semantic Compatibility Declaration is absent, invalid, or used
  outside its approved scope;
- an RFC-011 scenario revision differs from replay provenance;
- migration coverage cannot be proven; or
- deterministic identity validation fails.

Fail-closed means:

- no revision is guessed;
- no old decoder is silently reused;
- no ambiguous fact enters `DecisionContext`;
- no outcome is fabricated or relabeled;
- no Strategy or feature receives provenance metadata;
- no economic settlement is calculated under a mismatched revision;
- no existing artifact is altered; and
- the rejection or exclusion remains explicit and auditable.

Failure of revision-dependent interpretation does not authorize deletion of
raw evidence or mutation of valid observations from other rounds.

Absence of RFC-014 provenance does not prevent legacy reproduction under the
original frozen contract. It prevents only an RFC-014-aware eligibility claim
or new consumption that requires RFC-014 provenance.

---

# 22. Validation Strategy

Validation shall prove the following independently.

## 22.1 Identity validation

- canonical Protocol Revision Identity reconstruction;
- sensitivity to every protocol semantic and decoder-contract field;
- stability of Protocol Revision Identity when a concrete compatible decoder
  implementation changes;
- deterministic Decoder Compatibility Binding reconstruction and scope;
- deterministic Semantic Compatibility Declaration reconstruction and scope;
- deterministic Activation Binding reconstruction;
- exact predecessor lineage;
- no duplicate or ambiguous identities; and
- stable canonical encoding.

## 22.2 Activation validation

- authoritative deployment evidence;
- correct network, genesis, and program binding;
- ordered non-overlapping intervals;
- explicit gaps rather than inferred continuity;
- deterministic round and context resolution; and
- fail-closed boundary ambiguity.

## 22.3 Observation validation

- accepted decoder matches revision;
- accepted Decoder Compatibility Binding covers the required account and field
  scope;
- governing protocol context and observation/read context are preserved and
  validated independently;
- a later read context does not overwrite an earlier governing revision;
- raw payload identity agrees with decoded representation;
- repeated reconstruction produces identical provenance;
- unsupported revisions are not mislabeled;
- normal Observer cadence and ordering remain unchanged; and
- no revision is inferred from values or timestamps.

## 22.4 RFC-012 validation

- predecessor and successor provenance validate independently;
- predecessor read context cannot substitute for predecessor governing
  protocol context;
- same-revision transitions remain behaviorally identical;
- authoritatively bound cross-revision transitions remain auditable;
- ambiguous transitions cannot create accepted finalized evidence;
- evidence remains excluded from normal snapshots; and
- capture mode and terminal disposition remain unchanged.

## 22.5 Dataset validation

- every round has exactly one revision disposition;
- segment boundaries and assignments reconstruct deterministically;
- observation and outcome revisions agree;
- mixed-revision conflicts fail closed;
- revision ambiguity remains independent from lifecycle and outcome
  completeness;
- semantically different fields are not silently normalized;
- every shared canonical fact references one accepted Semantic Compatibility
  Declaration issued by the Protocol Provenance Authority;
- Dataset Builder and consumer policies cannot broaden that declaration;
- Dataset Revision Manifest participates in dataset identity; and
- migrated artifacts do not modify historical bytes or identities;
- legacy reproduction remains possible without being reported as RFC-014-aware
  eligibility; and
- only an accepted successor provenance artifact can establish a legacy
  dataset's RFC-014-aware eligibility.

## 22.6 Replay and future-information validation

- Replay rejects unsupported or ambiguous semantic inputs;
- eligible snapshot ordering is unchanged;
- `DecisionContext` is unchanged for identical eligible facts;
- revision provenance never appears in `DecisionContext`;
- feature inputs contain no revision or activation proxy;
- Strategy outputs remain identical for identical contexts; and
- outcomes remain unavailable until the existing revelation boundary.

## 22.7 RFC-011 and RQ-003 validation

- RFC-011 rejects scenario and replay revision mismatch;
- economic models remain deterministic within each revision;
- mixed datasets are divided into homogeneous economic intervals;
- no automatic participant-state transition crosses activation;
- RQ-003 reports revision strata and exclusions;
- revision does not enter feature or ranking inputs; and
- per-revision and pooled research claims remain distinguishable.

---

# 23. Risks

## 23.1 Incorrect activation authority

The greatest risk is assigning source semantics to the wrong on-chain interval.
A precise but unsupported boundary would make every downstream identity
deterministically wrong.

Mitigation is architectural: source identity and Activation Binding remain
separate, activation evidence must be authoritative, and uncertainty remains
explicit.

## 23.2 Semantic normalization

Consumers may be tempted to map identically located numeric fields into one
name. This can erase the distinction between parimutuel winnings and returned
principal.

RFC-014 permits shared canonical facts only after explicit equivalence proof
and preserves original revision-specific interpretation.

## 23.3 Provenance leakage into prediction

Revision strongly correlates with chronology and may correlate with changed
participant behavior. Exposing it to a feature or Strategy would violate
RQ-003's intended information protocol and could create an identity proxy.

RFC-014 confines revision to eligibility, audit, stratification, and economic
model selection.

## 23.4 Accidental pooling

A cumulative dataset can make incompatible regimes appear homogeneous.

Immutable segment manifests, consumer eligibility policies, and mandatory
per-revision reporting prevent silent pooling.

## 23.5 Historical ambiguity

Old data may lack sufficient evidence to prove an exact activation boundary.
RFC-014 preserves those observations but does not convert uncertainty into a
known assignment.

## 23.6 Identity and operational complexity

Additional identities increase validation and migration complexity. Limiting
the provenance model to revision, activation, observation, and dataset
manifest responsibilities avoids redesigning existing execution components.

## 23.7 Future incompatible winner semantics

The currently assessed successor retains the 25-square winning rule. A future
revision may not. RFC-014 therefore requires compatibility to be proven per
fact rather than declaring Replay or Evaluator permanently compatible.

---

# 24. Alternatives Considered

## 24.1 Documentation only

Document the source revision used by each analysis without changing artifact
provenance.

**Rejected.** Documentation cannot prevent a decoder from assigning the wrong
meaning to byte-compatible fields or make conflicting joins fail closed.

## 24.2 Replace the global revision constant

Update the repository from the Version 1.0 pin to the latest official source
revision.

**Rejected.** This supports only one moment in time, obscures historical
semantics, and repeats the same failure on the next protocol change.

## 24.3 Implementation-only propagation

Add revision fields independently to Observer, datasets, and economics without
a common architectural contract.

**Rejected.** Identity ownership, activation authority, mixed-revision rules,
future-information exclusion, and migration behavior would remain implicit and
could diverge across components.

## 24.4 Separate all datasets permanently

Use one physical dataset per protocol revision and prohibit cumulative
containers.

**Not selected as the complete architecture.** This is the safest initial
migration form, but it fragments cumulative history and does not define shared
provenance needed for explicit cross-revision research.

## 24.5 One normalized cross-revision schema

Translate every revision into one unqualified set of field meanings.

**Rejected.** Some facts are not semantically equivalent. Normalization would
erase authoritative source meaning and weaken deterministic reconstruction.

## 24.6 Expose revision to Strategy

Allow Strategy or features to react to protocol revision.

**Rejected.** Revision is provenance and an audit stratum. It is also a strong
chronology proxy. Exposing it would change RFC-010 and violate RQ-003's
decision-time research boundary.

## 24.7 Recommended approach

Adopt one immutable revision and activation provenance contract, permit both
revision-specific datasets and cumulative manifests, keep execution components
separated, and require every consumer to declare compatibility.

---

# 25. Implementation Phases

These phases define bounded architectural sequencing only. They do not specify
classes, modules, storage schema, commands, or implementation techniques.

## Phase 1 — Protocol revision identity

Establish:

- immutable Protocol Revision Identity;
- immutable Activation Binding;
- Protocol Provenance Authority acceptance;
- immutable Decoder Compatibility Bindings separate from Protocol Revision
  Identity;
- immutable Semantic Compatibility Declarations with one authoritative owner;
- canonical encoding and deterministic identities;
- official source and on-chain activation distinction;
- supported revision lineage; and
- validation for gaps, overlaps, conflicts, and ambiguity.

Phase 1 shall not modify Observer, RFC-012, Dataset Builder, Replay, RQ-003, or
RFC-011 execution.

## Phase 2 — Observer provenance

Bind accepted normal protocol observations to:

- Protocol Revision Identity;
- Activation Binding;
- accepted Decoder Compatibility Binding;
- governing protocol context distinct from observation/read context; and
- deterministic Observation Revision Provenance.

Preserve existing Observer behavior, ordering, persistence, and passive
operation.

## Phase 3 — RFC-012 evidence

Generalize RFC-012 evidence provenance to supported revisions while preserving:

- canonical predecessor identity;
- transition and response identities;
- context-bound zero-or-one predecessor observation;
- same-revision and authoritatively proven cross-revision transitions;
- outcome-only consumption; and
- existing terminal dispositions and capture modes.

## Phase 4 — Dataset Builder

Introduce deterministic Dataset Revision Manifest production and validation.
Establish revision-consistent lifecycle and outcome joins, homogeneous segment
assignment, consumption of accepted Semantic Compatibility Declarations, and
additive legacy migration.

Preserve the decision-snapshot freeze and existing outcome-only boundary.

## Phase 5 — Replay validation

Add revision compatibility and eligibility validation before DecisionContext
construction. Support explicit mixed-revision dataset policies while proving:

- unchanged replay ordering;
- unchanged DecisionContext;
- no provenance leakage; and
- deterministic exclusions and artifact identities;
- preservation of legacy reproduction; and
- separation of legacy reproduction from RFC-014-aware replay eligibility.

## Phase 6 — RQ-003 and RFC-011 integration

Complete consumption at the two downstream boundaries:

- RQ-003 revision strata, dataset controls, comparison rules, and reporting;
  and
- RFC-011 revision-matched replay facts, homogeneous economic intervals, and
  model identity validation.

Phase 6 shall not change Strategy interfaces, feature inputs, ranking behavior,
or RFC-011's separation from RFC-010.

---

# 26. Acceptance Criteria

RFC-014 is architecturally complete when all of the following can be proven:

1. one canonical Protocol Revision Identity reconstructs exact official source
   semantics and decoder-contract identity without depending on a concrete
   decoder implementation;
2. one immutable Activation Binding distinguishes source history from deployed
   network authority;
3. every concrete decoder is authorized through a separate immutable Decoder
   Compatibility Binding;
4. one Protocol Provenance Authority owns every accepted Semantic Compatibility
   Declaration, and consumers cannot broaden it;
5. every semantically accepted new observation carries deterministic revision
   provenance and preserves governing protocol context separately from
   observation/read context;
6. unsupported or ambiguous revisions cannot be mislabeled as the prior pin;
7. RFC-012 evidence binds predecessor and successor provenance without changing
   its observation budget or outcome-only boundary;
8. a post-activation predecessor read does not overwrite the predecessor's
   governing revision;
9. every replay round has one deterministic known, ambiguous, or unsupported
   revision disposition;
10. lifecycle and outcome joins fail closed on revision conflict;
11. a Dataset Revision Manifest reconstructs all segment boundaries and
   assignments deterministically;
12. mixed-revision physical storage cannot silently become semantically pooled
   input;
13. Replay validation admits only explicitly supported revision facts;
14. legacy reproduction remains distinct from RFC-014-aware replay eligibility;
15. `DecisionContext` remains unchanged and contains no revision provenance;
16. features, Strategy, and ranking receive no revision or activation signal;
17. RFC-010 experiments remain deterministic and reproducible;
18. one RFC-011 Economic Scenario consumes only matching-revision rounds;
19. economic simulation does not carry participant state across activation
    without separately defined authority;
20. RQ-003 treats revision only as audit, eligibility, stratification, and
    reporting information;
21. per-revision and pooled research claims remain explicitly distinguishable;
22. legacy artifacts remain immutable and reproducible;
23. migration creates successor provenance identities without rewriting
    historical data; and
24. no RFC-010, RFC-011, RFC-012, or RQ-003 future-information invariant is
    weakened.

Completion of this RFC does not itself approve a specific successor protocol
revision, establish its on-chain activation boundary, authorize dataset
migration, or authorize production deployment.

---

# 27. Architectural Conclusion

ORE Miner V3 shall treat protocol revision as first-class immutable provenance
at the boundaries where protocol facts are captured, interpreted, joined,
validated, researched, and settled.

Source semantics and on-chain activation remain distinct. Every known round is
bound to one supported revision through authoritative activation evidence.
Ambiguity remains explicit and fails closed.

Protocol semantic identity also remains distinct from local decoder
implementation identity. The Protocol Provenance Authority owns immutable
decoder compatibility and cross-revision semantic compatibility declarations;
all downstream components consume those declarations without redefining them.

Governing protocol context determines which revision gave a fact its meaning.
Observation/read context proves when the bytes were obtained and never
overwrites that governing context.

Replay and Strategy Lab remain structurally unchanged. Protocol provenance is
validated before `DecisionContext` construction and retained for audit, but it
never becomes a DecisionContext, feature, Strategy, or ranking input. RFC-012
continues to attach post-transition evidence only at the outcome boundary.
RFC-011 continues to own all revision-specific economics. RQ-003 uses revision
only to define valid research populations and claims.

This minimal provenance layer allows immutable historical revisions to coexist
without semantic erasure, preserves deterministic reconstruction, and makes
future official protocol changes explicit rather than implicit.

Legacy artifacts retain reproducibility under their original frozen contracts.
Only separately accepted successor provenance establishes eligibility for new
RFC-014-aware Replay, research, or economic use.
