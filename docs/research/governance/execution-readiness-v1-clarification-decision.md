# Execution Readiness v1 Clarification Governance Decision

## Status

- Type: Execution Readiness governance decision
- State: Proposed for adversarial review
- Decision identifier: `execution-readiness-v1-clarification-decision`
- Governing source checkpoint: `4bfd568bbeabc58aa400b2b7c3ad4d0e12be4434`
- Existing frozen specification: [Experiment Execution Readiness Specification v1](../specifications/experiment-execution-readiness-v1.md)
- Existing frozen specification revision: `experiment-execution-readiness-v1`
- Existing frozen specification SHA-256: `6aea25aac1b701619bde4db309fdeb341a4fc3fd790e6ee9fcfa4414e9a9db6b`
- Clarified specification revision selected by this decision: `experiment-execution-readiness-v1.1`
- Clarified specification path selected by this decision: `docs/research/specifications/experiment-execution-readiness-v1.1.md`
- Implementation authorized by this document: No
- Specification drafting authorized by this document after approval: Yes

This document freezes the governance choices needed to draft a complete,
internally consistent v1.1 specification. It does not amend v1 by itself,
authorize Phase 3C implementation, or authorize experiment execution. Until
this decision and the resulting v1.1 specification are reviewed, frozen, and
remote-backed, the current v1 specification remains the only specification
authority and Phase 3C Slice 1 remains blocked.

## 1. Governing context

This decision is governed by:

- the immutable [Experiment Execution Readiness Specification v1](../specifications/experiment-execution-readiness-v1.md), especially Sections 3.8, 4.3–4.4, 6.2–6.5, 10–13, 16, 20, and 21;
- the [Phase 3B handoff checkpoint](../../project-checkpoints/ore-v3-execution-readiness-phase3b-handoff.md);
- the immutable-specification rule in [RQ-003 Research Execution Specification v1](../specifications/rq003-research-execution-specification.md), Section 3.1; and
- the additive-revision precedent in [RQ-003 Research Execution Specification v2](../specifications/rq003-research-execution-specification-v2.md), Section 8.

The authority order is the frozen specification, the tracked checkpoint where
it establishes an explicit continuation constraint, already frozen committed
contracts incorporated by the specification, and historical material as
non-normative evidence of intent. Uncommitted Slice-1 schemas and tests are not
authority.

## 2. Problem statement

Phase 3C Slice 1 exposed four places where independent implementations cannot
derive the same canonical object from v1 alone:

1. v1 requires `attempt_identity` to bind `output_namespace_identity`, while
   the realized namespace maps `attempt_identity`, but v1 defines no identity
   domain or canonical material for `output_namespace_identity`;
2. v1 names readiness, current-readiness, and launch dispositions but does not
   define their exact representation in the canonical failure receipt or a
   bounded vocabulary for failed and completed checks;
3. v1 defines broad terminal `FAILED` semantics and recovery behavior but does
   not define a stable canonical failure-class and recovery representation;
4. v1 does not state whether supported attempt kinds constrain every reusable
   authority contract structurally or constrain the authority selected for a
   particular attempt.

Encoding any of these choices only in a schema or Python validator would make
that implementation, rather than the governed specification, the source of
normative semantics. This decision supplies only the missing precision. It
does not change the authority chain, lifecycle ordering, outcome boundary,
scientific validity rules, or Phase 3C endpoint.

## 3. Decision summary

The following choices are selected for incorporation into v1.1:

1. `allocation_authority_identity` identifies one unique repository-bound
   authority instance, distinct from reusable allocator-contract identity.
   `output_namespace_identity` identifies pre-attempt allocation coordinates,
   not the realized path. Its material is the minimal seven-field object in
   Section 4. It is derived before `attempt_identity`. The realized namespace
   is reserved atomically with the receipt and maps the resulting
   `attempt_identity` without feeding back into namespace identity.
2. Failure receipts have three closed classes:
   `READINESS_REJECTED`, `CURRENT_READINESS`, and `LAUNCH_REJECTED`. They use
   one fixed, ordered 27-invariant vocabulary and one complete status vector.
   A control failure before evaluator entry or during canonical serialization
   fails closed as `CANONICAL_RECEIPT_UNAVAILABLE` and cannot fabricate a
   receipt.
3. Terminal `FAILED` has four stable, precedence-ordered classes with closed
   embedded failure evidence and a canonical coherent-or-conflicting control
   history snapshot:
   `infrastructure_failure`, `interruption`, `ambiguous_state`, and
   `validity_not_established`. Recovery mode is an orthogonal two-value field,
   never a failure class.
4. A reusable attempt-authority contract may support any nonempty canonical
   subset of `official` and `reproduction`. Suitability for the requested
   attempt kind is a readiness/launch cross-contract invariant.
5. v1.1 adds exactly one normative schema object kind,
   `output-namespace-identity-material`, making the complete target registry
   29 schemas. No separate failure-code, failure-control-evidence,
   recovery-evidence, or namespace-realization schema is added by this
   clarification.
6. The clarification is published as a new immutable consolidated
   specification at
   `docs/research/specifications/experiment-execution-readiness-v1.1.md` with
   revision `experiment-execution-readiness-v1.1`. Frozen v1 is not edited.

## 4. Output-namespace identity decision

### 4.1 Problem and alternatives considered

V1 Section 3.8 requires one shared allocation authority to atomically create
permanent kind-specific ordinals, attempt identities, allocation receipts,
and output-namespace identities. Sections 6.5 and 11.3 require attempt identity
to bind an already-derived namespace identity and prohibit cross-object
identity cycles. Section 16.1 requires the final write-once namespace to
encode or unambiguously map experiment, kind, ordinal, and attempt identity.

The alternatives considered were:

1. derive namespace identity from `attempt_identity`, which is cyclic because
   attempt identity already binds namespace identity;
2. derive namespace identity from every launch authority and input field also
   present in attempt identity, which is acyclic but redundant and larger than
   needed for namespace uniqueness;
3. identify only a generic namespace policy, which cannot distinguish two
   allocations;
4. identify the final realized path, which cannot be derived before attempt
   identity and confuses identity with storage realization; or
5. identify the minimal pre-attempt allocation coordinates under the selected
   authority, allocator contract, and output policy, then realize the final
   namespace after attempt identity exists.

Alternative 5 is selected. It is the only alternative that satisfies all four
v1 clauses without a cycle, placeholder, or duplicate authority graph.

### 4.2 Exact semantic purpose

`output_namespace_identity` identifies the canonical allocation coordinates
from which one output namespace must be reserved. It is distinct from:

- the output policy, which defines how those coordinates and the later
  attempt identity are mapped to storage;
- the `attempt_identity`, which binds the complete launch authority and exact
  attempt inputs; and
- the realized namespace or path, which is an operational write-once storage
  realization and never establishes authority by its name.

The namespace identity exists to give the attempt and allocation receipt a
cycle-free, content-derived reference to the unique output reservation that
the allocator must atomically create.

### 4.3 Allocation-authority instance identity

`allocation_authority_identity` identifies one unique configured allocation-
authority instance, not a reusable allocator contract and not merely the bytes
of an allocator implementation. Option A is selected because it gives the
shared ordinal ledger and control-storage authority one stable identity while
keeping repository/research authority out of every downstream namespace
material as a redundant second field.

Its canonical identity material contains exactly these required fields in
canonical object-key order:

1. `allocation_authority_identifier` — a stable identifier unique within the
   bound repository/research authority. It is an ASCII lowercase,
   case-sensitive string of 1 through 64 code points matching exactly
   `[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*`. It is therefore already NFC. Whitespace,
   path separators, leading or trailing separators, consecutive separators,
   percent encoding, and alternate case are prohibited;
2. `allocation_authority_schema_revision` — exactly
   `allocation-authority-identity-material-v1`; and
3. `repository_authority_identifier` — the repository-governed identity from
   Section 3.5 of v1, which also defines the research authority within which
   the ordinal ledger is shared.

The identifier is derived as:

```text
SHA256(
  UTF8("orev3:experiment-attempt-allocation-authority:v1\n")
  || canonical(allocation_authority_identity_material)
)
```

The material object is a closed definition inside the normative
`attempt-authority-contract` schema. It is not a separately stored control
object and does not add a schema-registry object kind. The contract stores and
binds the resulting `allocation_authority_identity`; Python validation
reconstructs it from the three fields above.

`allocator_contract_identity` remains separate. It identifies reusable
allocation semantics and implementation bindings. Multiple unique authority
instances MAY use one byte-identical allocator contract, but their distinct
repository/authority-identifier pairs yield distinct allocation-authority
identities. One authority instance MAY adopt a different allocator contract
only through a newly governed readiness state; doing so does not change the
identity of the existing permanent ordinal ledger.

The uniqueness scope is global across the repository authorities recognized
by this readiness control plane: repository authority identifiers are unique,
and allocation-authority identifiers are unique within each repository
authority. Two distinct authority instances therefore cannot share an
`allocation_authority_identity`, even when they use the same contract and each
selects the same experiment, kind, and ordinal.

Repository governance MUST maintain one closed mapping from each
`(repository_authority_identifier, allocation_authority_identifier)` pair to
exactly one shared authority instance. Duplicate pairs, multiple backend
resolutions for one pair, or executors resolving the pair to different ordinal
ledgers fail `attempt_policy`. Machine-local aliases, endpoints, credentials,
and storage paths remain transport configuration outside identity. This
cross-executor uniqueness check is semantic conformance beyond JSON Schema.
Changing a backend or transport for the same pair is a ledger migration, not a
new authority: the complete permanent ordinal, receipt, reservation, and
control history MUST be preserved and continuity-proven before the replacement
can resolve for that pair. An empty, reset, forked, or partially migrated
backend MUST fail `attempt_policy` and MUST NOT allocate.

### 4.4 Exact namespace canonical material

The new canonical object kind is
`output-namespace-identity-material`. Its exact required fields, in canonical
JSON object-key order, are:

1. `allocation_authority_identity` — the content identity of the one shared
   unique allocation-authority instance defined by Section 4.3;
2. `allocator_contract_identity` — the content identity of the governed
   allocator contract that defines atomic allocation semantics;
3. `attempt_kind` — exactly `official` or `reproduction`;
4. `experiment_identifier` — the normalized experiment identifier;
5. `output_namespace_schema_revision` — exactly
   `output-namespace-identity-material-v1`;
6. `output_policy_revision` — the exact governed output-policy revision bound
   by the readiness record; and
7. `permanent_ordinal` — the positive permanent kind-specific ordinal selected
   atomically by the allocation authority.

No other field is permitted. In particular, the material MUST NOT contain
`attempt_identity`, allocation-receipt identity, realized path, machine-local
root, credential, timestamp, operator value, readiness identity, `S`, `R`,
`H`, launch-authority snapshot identity, or immutable input snapshot
identities.

Readiness identity, `S`, `R`, `H`, launch authority, and input snapshots are
not omitted from attempt authority: Sections 6.5 and 11.3 already require them
in `attempt_identity_material` and the allocation receipt. Repeating them in
namespace identity would not increase uniqueness or authority. Permanent
ordinals are never reused under one allocation authority and experiment/kind
scope; the authority, contract, experiment, kind, ordinal, schema revision,
and output policy are therefore the smallest sufficient deterministic
namespace coordinates.

### 4.5 Exact namespace identity and domain

Let `N` be the Section 4.4 object serialized under the v1 canonical JSON rules,
including its trailing LF. The identity is:

```text
SHA256(
  UTF8("orev3:experiment-output-namespace:v1\n")
  || N
)
```

The lowercase hexadecimal result is `output_namespace_identity`. The identity
material object does not store that result and therefore has no self-cycle.

### 4.6 Exact derivation and realization order

Within one atomic allocation transaction, the logical derivation order is:

```text
validated launch-authority snapshot
+ ordered immutable input snapshot identities
+ selected attempt authority and allocator contract
  -> allocate the next permanent experiment/kind ordinal
  -> output_namespace_identity_material
  -> output_namespace_identity
  -> attempt_identity_material
  -> attempt_identity
  -> allocation-receipt material
  -> allocation_receipt_identity
  -> atomically persist the receipt and reserve the final namespace
  -> final write-once namespace realization that encodes or maps
     experiment + kind + ordinal + attempt_identity
```

These computations and writes are one atomic compare-and-create operation for
the purposes of Sections 3.8 and 11.3. “Derived before” describes the acyclic
identity dependency order; it does not permit a partially authoritative
namespace or ordinal to escape the transaction.

The realized namespace MUST be deterministically selected by the governed
output policy and MUST map all four Section 16.1 values. It MUST also be
cross-checked against `output_namespace_identity`. Its path or storage key is
operational material and does not participate in namespace identity,
readiness identity, or scientific identity. Existing targets remain collisions
and no overwrite, suffix, reuse, or merge is permitted.

### 4.7 Compatibility and consequences

This decision makes the cycle prohibition in Section 6.5 executable and
preserves Sections 3.8, 11.3, and 16.1. It does not alter attempt identity
material or remove any authority field from it.

V1.1 must:

- add both domains and derivations above to Section 6.5;
- distinguish namespace identity from realization in Sections 3.8, 11.3, and
  16.1;
- add the normative schema described in Section 8; and
- require tests for deterministic reconstruction, cross-executor equality,
  no cycles, atomic no-replace realization, and collision rejection.

## 5. Failure-receipt decision

### 5.1 Problem and alternatives considered

V1 distinguishes pre-seal rejection, derived current readiness, and launch
rejection, but Section 13 does not assign these concepts to an exact closed
receipt shape. Arbitrary failed-invariant or check strings would provide a
channel for outcomes, exceptions, diagnostics, or encoded payloads.

The alternatives were free-form strings, an implementation-owned registry, a
separate governed code-registry object, or a finite specification-owned
vocabulary. The finite specification-owned vocabulary is selected because the
checks correspond to stable sections of the readiness contract and must be
interoperable. A separate registry would add indirection without allowing any
legitimate runtime extension: adding a normative invariant requires a new
specification revision in all cases.

For the one policy-conditional invariant, `launch_smoke`, the alternatives
were also evaluated explicitly. Fixing its final applicability at evaluator
entry would require trusting an as-yet-unvalidated sealed record. Adding a
fifth `applicability_not_established` status would distinguish evaluator
internals that have the same canonical authority consequence, but would add
state without improving a receipt's truth. Treating every empty smoke policy
as an applicable successful no-op would misstate v1 Section 15.2, under which
the smoke subset exists only when required by the bound mandatory policy.
Progressive applicability is therefore selected: stage applicability is fixed
at entry, policy-conditional applicability is established only by the owning
governed invariant, and `not_evaluated` makes no claim about applicability.

### 5.2 Exact receipt classes

The canonical field is `receipt_class`, with exactly these values:

1. `READINESS_REJECTED` — isolated preparation or candidate construction
   failed before a seal/current-readiness object existed;
2. `CURRENT_READINESS` — a status/current-readiness resolution produced one
   non-ready Section 10 disposition; and
3. `LAUNCH_REJECTED` — an official launch failed before allocation.

`CURRENT_READINESS` is a receipt class, not a lifecycle state or current-
readiness disposition. `READINESS_REJECTED` and `LAUNCH_REJECTED` retain their
v1 meanings.

The required `current_readiness_disposition` domain is branch-specific:

| Receipt class | Permitted value |
| --- | --- |
| `READINESS_REJECTED` | exactly `not_applicable` |
| `CURRENT_READINESS` | exactly one of the eight non-ready dispositions below |
| `LAUNCH_REJECTED` | one of the eight non-ready dispositions, or `EXECUTION_READY` when current readiness passed and a launch-only invariant failed |

The eight non-ready values retain the exact precedence order from v1
Section 10:

1. `READINESS_UNRESOLVED_REMOTE`
2. `READINESS_AMBIGUOUS`
3. `READINESS_INVALID_RECORD`
4. `READINESS_ORPHANED`
5. `SUPERSEDED`
6. `READINESS_STALE`
7. `READINESS_INPUT_MISMATCH`
8. `READINESS_BLOCKED_INPUT_UNAVAILABLE`

`EXECUTION_READY` is never a failure. Its presence in a `LAUNCH_REJECTED`
receipt says only that the preceding current-readiness step succeeded before a
subsequent launch-only invariant failed.

### 5.3 Exact common structure

Every receipt has exactly these semantic fields, all required and non-null:

- schema revision and receipt identity;
- `receipt_class`;
- normalized experiment identifier;
- candidate source commit as a closed tagged branch of `known` plus the exact
  commit, or `absent` with no value;
- readiness identity as the same closed `known`/`absent` branch;
- launch-authority snapshot identity as the same closed `known`/`absent`
  branch;
- repository authority identifier and full approved branch ref;
- `current_readiness_disposition` under Section 5.2;
- one `failed_invariant_identifier` from Section 5.4;
- the complete ordered `check_statuses` vector from Section 5.6;
- `scientific_execution_started=false`; and
- `scientific_outcome_evidence=absent`.

The three availability bindings are closed discriminated objects, not empty
strings, SHA-shaped placeholders, nullable fields, or an unrestricted union.
No diagnostic, message, exception, path, host, operator, timestamp, outcome,
label, result, or arbitrary extension field is permitted.

### 5.4 Exact invariant/check vocabulary and canonical order

`failed_invariant_identifier` and every `check_statuses[].check_identifier`
use this same exact finite vocabulary and order:

1. `schema_registry`
2. `experiment`
3. `git_authority`
4. `readiness_specification`
5. `control_plane`
6. `source_scopes`
7. `protocol`
8. `implementation`
9. `execution_specification`
10. `execution_profile`
11. `runtime`
12. `configuration`
13. `external_inputs`
14. `replay`
15. `artifacts`
16. `outcome_policy`
17. `validation`
18. `attempt_policy`
19. `canonical_readiness_record`
20. `readiness_seal_and_ancestry`
21. `current_external_inputs`
22. `launch_authority_snapshot`
23. `launch_input_snapshots`
24. `control_storage`
25. `output_namespace`
26. `launch_smoke`
27. `second_fetch`

Identifiers 1–18 correspond in order to the required readiness-record
sections in v1 Section 6.2. Identifier 19 validates the assembled record,
canonical bytes, and identity. Identifiers 20–21 cover Sections 3.3, 5.6,
7, 9, and 10. Identifiers 22–27 cover the launch-only sequence in Sections
3.6, 7.3, 9.2, 11.2, 15.2, and 16.

`internal_control` is deliberately not a canonical invariant identifier.
Model A is selected, with an explicit canonical-receipt availability boundary.
Evaluator entry is permitted only after the fixed receipt class, normalized
experiment identifier, repository authority/ref, v1.1 failure-receipt schema,
and canonical serializer are available and the serializer's deterministic
self-check succeeds. None of those prerequisites counts as a passed invariant.
For each receipt class, successful entry atomically fixes the receipt class and
every stage-defined applicability fact and makes that class's first invariant
`active` before any fallible invariant work begins. The sole applicability fact
not fixed at entry is the policy-conditional `launch_smoke` fact for
`LAUNCH_REJECTED`; Section 5.6 defines its progressive authoritative
resolution. The first active invariant is `git_authority` for all three
classes. A control-machinery failure while an invariant is active normalizes to
that invariant. Transition to the next invariant atomically makes the next
invariant that is not already proven inapplicable active before any fallible
transition work; a failure between completed checks therefore normalizes to
the next invariant, never to a completed one. An invariant becomes `passed`
only when the next invariant has atomically become active, or, for the final
invariant, when the successful result has been completely constructed and
returned. The final invariant remains active during fallible success-result
construction, so a failure in that interval normalizes to it rather than
fabricating a completed vector.

A failure before evaluator entry cannot truthfully produce the required vector
because no invariant was active and no check passed. A failure while building
or canonically serializing the receipt likewise cannot produce canonical
receipt bytes. In either case the operation MUST fail closed with the fixed
noncanonical control-plane result `CANONICAL_RECEIPT_UNAVAILABLE`: it returns no
receipt identity, no readiness or launch disposition with canonical authority,
no candidate, no allocation, and no scientific execution. This result is an
implementation/conformance failure, not a fourth receipt class, lifecycle
state, scientific result, or identity-bearing object. It accepts no message,
code extension, or diagnostic payload. Frozen-v1 Section 13's canonical-receipt
obligation remains mandatory whenever canonical bytes can be constructed; the
implementation MUST NOT fabricate a vector when that obligation is impossible
to fulfill.

After an invariant has failed, its selected invariant and complete vector are
fixed. Failure to persist already serialized canonical receipt bytes does not
invalidate those bytes: the bytes MUST still be returned as Section 13
requires. Failure before those bytes have been serialized, including serializer
failure, returns only `CANONICAL_RECEIPT_UNAVAILABLE`. Raw internal errors may
be retained as noncanonical diagnostics subject to outcome and secret controls,
but never enter either result.

This rule is not an escape hatch: implementations cannot select another
identifier merely because an exception originated in shared code. The active
invariant is fixed by the canonical evaluation state machine below. Exception
type, message, stack, and implementation location never enter the receipt.

This vocabulary is normative and complete for v1.1. An implementation may
retain richer secondary diagnostics outside the canonical receipt, subject to
outcome and secret controls, but those diagnostics have no readiness,
scientific, or identity authority. A new canonical invariant requires a new
specification revision; adapters cannot extend the vocabulary.

### 5.5 Exact `schema_registry` and `canonical_readiness_record` ownership

The two invariants are disjoint. `schema_registry` owns the repository-governed
registry at `S`; `canonical_readiness_record` owns one candidate or sealed
readiness-record object. The exact mapping is:

| Governed failure | Sole owning invariant |
| --- | --- |
| Governed registry component/policy cannot be reconstructed at `S` | `schema_registry` |
| Registry bytes malformed or noncanonical | `schema_registry` |
| Registry identifier or revision absent, malformed, or unsupported | `schema_registry` |
| Registry membership incomplete, excessive, duplicated, or noncanonically ordered | `schema_registry` |
| Required readiness-record schema entry absent or duplicated | `schema_registry` |
| Structurally valid registry section declares the wrong readiness-record schema identifier or revision | `schema_registry` |
| Any registry schema identifier, path, byte count, digest, Git blob, or actual bytes disagree | `schema_registry` |
| A governed schema cannot be resolved or does not itself satisfy its declared JSON Schema dialect/identity | `schema_registry` |
| Candidate or sealed readiness-record bytes absent at the lifecycle-required source/path | `canonical_readiness_record` |
| Candidate or sealed record bytes malformed, noncanonical, or not UTF-8 canonical JSON | `canonical_readiness_record` |
| Candidate or sealed record has an unknown or missing field at any record-owned level | `canonical_readiness_record` |
| Candidate or sealed record fails validation against the readiness-record schema already fixed by the applicable v1.1 contract | `canonical_readiness_record` |
| Stored `readiness_identity` is absent, malformed, self-included, or differs from independent reconstruction | `canonical_readiness_record` |
| Sealed record blob differs from the candidate bytes or fails the same canonical/schema/identity reconstruction | `canonical_readiness_record` |

A record's `schema` section is record-owned structure, so its absence or wrong
closed shape is `canonical_readiness_record`. Once that section is structurally
valid, any false claim about registry identifier/revision, membership,
readiness-record schema identifier/revision, paths, bytes, digests, or Git
blobs is `schema_registry`. The readiness-record schema therefore enforces the
closed scalar/collection shape of the registry section but does not use a
`const` to preempt the semantic registry-policy comparison; the exact values
are enforced by `schema_registry`. Other record sections are first checked for
record-schema shape by `canonical_readiness_record`; their semantic and
cross-object truth is owned by their corresponding later invariant. Thus one
malformed byte representation cannot be reassigned to a semantic invariant,
and one structurally valid but false binding cannot be hidden as a generic
record failure.

V1.1 defines no separate stored schema-registry control object. The
repository-owned registry component at `S` produces one normalized policy
consisting of the registry identifier, canonical-encoding revision, and exact
ordered 29 declarations; the readiness record binds that same declaration.
"Registry absent" means that governed component/policy or one of its required
schema documents cannot be reconstructed at `S`, not that an additional
registry file must exist.

During Phase 3C readiness validation, `schema_registry` runs before candidate
assembly and `canonical_readiness_record` runs last. During current-readiness
and launch resolution, the implementation uses the specification-fixed v1.1
readiness-record schema semantics to validate the fetched record object first;
it does not trust the record to define its own validator. It then validates the
record's structurally valid registry declaration and the exact governed schema
artifacts at `S` under `schema_registry`. No unsupported record-declared schema
can bootstrap authority.

### 5.6 Complete status vector

`check_statuses` contains exactly 27 entries in the order in Section 5.4,
with no duplicate or omitted identifier. Each status is exactly one of:

- `passed`;
- `failed`;
- `not_evaluated`; or
- `not_applicable`.

The four statuses have exactly these canonical meanings:

- `passed`: authoritative applicability was established, the invariant was
  evaluated, and it succeeded;
- `failed`: authoritative applicability was established, the invariant was
  evaluated, and it was the first failed invariant in the class-specific
  evaluation order;
- `not_evaluated`: evaluation produced no authoritative pass, failure, or
  inapplicability determination for this invariant before the receipt's first
  failure stopped progression. This status deliberately makes no claim about
  whether applicability would have been established later; and
- `not_applicable`: stage authority or a successfully validated governed
  applicability prerequisite affirmatively established that the invariant
  does not apply in this receipt context.

The evaluator internally distinguishes an invariant whose applicability has
not yet been established from an invariant already proven applicable but not
yet reached. The canonical receipt normalizes both to `not_evaluated` because
the sole authority fact common to both is that no pass, failure, or governed
inapplicability determination was reached. This is one meaning, not two:
`not_evaluated` never asserts applicable, inapplicable, passed, or failed.

Exactly one entry is `failed`, and its identifier equals
`failed_invariant_identifier`. Section 5.4 fixes vector serialization order;
the dependency-correct evaluation order is fixed separately for each receipt
class below. Evaluation stops for authority purposes at the first applicable
failure. Applicable checks preceding it in that class's evaluation order are
`passed`; later checks for which no terminal determination was reached are
`not_evaluated`. Checks affirmatively proven inapplicable are
`not_applicable`. Parallel or secondary observations do not change this
primary canonical vector.

Stage applicability is fixed before evaluation. Governed conditional
applicability is fixed progressively only by successful evaluation of its
specified owning prerequisite. Neither form can be changed by an adapter, an
implementation exception, or runtime convenience:

| Identifier range | `READINESS_REJECTED` | `CURRENT_READINESS` | `LAUNCH_REJECTED` |
| --- | --- | --- | --- |
| 1–19 | applicable | applicable | applicable |
| 20–21 | `not_applicable` | applicable | applicable |
| 22–25 | `not_applicable` | `not_applicable` | applicable |
| 26 `launch_smoke` | `not_applicable` | `not_applicable` | unresolved until `validation` passes; governed conditional rule below |
| 27 `second_fetch` | `not_applicable` | `not_applicable` | applicable |

For `READINESS_REJECTED`, the exact evaluation order is:

```text
git_authority
-> readiness_specification
-> schema_registry
-> experiment
-> control_plane
-> source_scopes
-> protocol
-> implementation
-> execution_specification
-> execution_profile
-> runtime
-> configuration
-> external_inputs
-> replay
-> artifacts
-> outcome_policy
-> validation
-> attempt_policy
-> canonical_readiness_record
```

This follows fresh authority, detached preparation/evidence reconstruction,
and final candidate assembly. No seal, current-readiness, or launch check
exists in that lifecycle stage.

For `CURRENT_READINESS`, the exact evaluation order is:

```text
git_authority
-> canonical_readiness_record
-> schema_registry
-> experiment
-> readiness_specification
-> control_plane
-> source_scopes
-> protocol
-> implementation
-> execution_specification
-> execution_profile
-> runtime
-> configuration
-> external_inputs
-> replay
-> artifacts
-> outcome_policy
-> validation
-> attempt_policy
-> readiness_seal_and_ancestry
-> current_external_inputs
```

`canonical_readiness_record` first performs exactly the record-owned checks in
Section 5.5 using the specification-fixed v1.1 schema semantics. The
structurally valid record then supplies `S` and its registry declaration for
the independently governed `schema_registry` check. Subsequent checks validate
each semantic section and cross-binding under Section 5.5 ownership. They do
not rerun Phase 3A/3B scientific preparation. This makes the prior evidence
authoritative only through its sealed record and current reconstruction; it is
neither blindly trusted nor scientifically re-executed.

For `LAUNCH_REJECTED`, evaluation uses the complete `CURRENT_READINESS` order
above followed exactly by:

```text
launch_authority_snapshot
-> launch_input_snapshots
-> control_storage
-> output_namespace
-> launch_smoke                 # omitted only when intrinsically inapplicable
-> second_fetch
```

If current readiness fails, its Section 10 disposition is bound and every
later applicable launch check is `not_evaluated`. Only after current readiness
passes may launch checks begin.

For `READINESS_REJECTED` and `CURRENT_READINESS`, `launch_smoke` is
stage-inapplicable and always `not_applicable`. For `LAUNCH_REJECTED`, its
applicability is initially unresolved and becomes authoritative only when the
`validation` invariant has successfully reconstructed and validated the
repository-owned mandatory readiness-test policy bound by the sealed record,
including its exact `launch_smoke_selectors` collection. The applicability
decision is committed atomically before `validation` becomes `passed`:

- an exact empty collection proves `launch_smoke` inapplicable, and its status
  is `not_applicable` in any later rejection receipt;
- a nonempty collection proves `launch_smoke` applicable. Its status remains
  `not_evaluated` until smoke execution is reached, becomes `passed` only after
  every selector succeeds, and becomes `failed` if it is the first failed
  invariant; and
- if evaluation stops before `validation` passes, including because the
  policy cannot be authoritatively reconstructed, `launch_smoke` is
  `not_evaluated`. An implementation MUST NOT inspect or trust unvalidated
  record or policy bytes merely to select a smoke status.

V1.1 must require the selector collection in the policy schema, sorted and
unique by stable selector; this directly implements v1 Section 15.2's fixed
launch-smoke subset. An adapter cannot add to, remove from, replace, or
otherwise change that repository-owned subset. No other identifier has
profile-, adapter-, policy-, or other progressively selected applicability.

Policy-reconstruction failure ownership follows Section 5.5 without creating
a smoke-specific exception. A missing or malformed record-owned policy field
is `canonical_readiness_record`; an unavailable or invalid governed schema
definition is `schema_registry`; and a structurally valid policy binding whose
governed policy artifact, identity, selectors, or required results cannot be
reconstructed or cross-validated is `validation`. In every branch,
`launch_smoke` is `not_evaluated` because the owning prerequisite did not pass.

Zero governed external inputs do not make `external_inputs`,
`current_external_inputs`, or `launch_input_snapshots` inapplicable. Their
validators reconstruct the exact empty canonical collection and return
`passed` when every empty-input invariant holds.

For every receipt class, the first failure in its exact order becomes
`failed_invariant_identifier`. Every preceding check that was authoritatively
applicable is `passed`; the selected check is `failed`; every later check for
which no authoritative terminal determination was reached is `not_evaluated`;
and every check affirmatively proven inapplicable is `not_applicable`
regardless of where evaluation stopped. The resulting entries are always
serialized in Section 5.4 vector order. No later observed or parallel error
changes the canonical first failure.

The following representative mappings are normative:

| Governed failure | Receipt class/disposition | Failed invariant |
| --- | --- | --- |
| Remote authority unavailable during readiness validation | `READINESS_REJECTED` / `not_applicable` | `git_authority` |
| Remote authority unavailable during current status or launch | `CURRENT_READINESS` or `LAUNCH_REJECTED` / `READINESS_UNRESOLVED_REMOTE` | `git_authority` |
| Registry artifact at `S` malformed, unsupported, incomplete, or missing the readiness-record schema during candidate construction | `READINESS_REJECTED` / `not_applicable` | `schema_registry` |
| The same registry defect is discovered in a sealed record | `CURRENT_READINESS` or `LAUNCH_REJECTED` / `READINESS_INVALID_RECORD` | `schema_registry` |
| Candidate bytes malformed, noncanonical, or readiness-identity inconsistent | `READINESS_REJECTED` / `not_applicable` | `canonical_readiness_record` |
| Sealed record bytes malformed, noncanonical, or readiness-identity inconsistent | `CURRENT_READINESS` or `LAUNCH_REJECTED` / `READINESS_INVALID_RECORD` | `canonical_readiness_record` |
| Experiment section absent or structurally malformed | `READINESS_REJECTED` / `not_applicable`, or sealed `READINESS_INVALID_RECORD` | `canonical_readiness_record` |
| Structurally valid experiment section has a false identifier/path/configuration binding | `READINESS_REJECTED` / `not_applicable`, or sealed `READINESS_INVALID_RECORD` | `experiment` |
| Structurally valid control-plane section has a false or unreconstructable component binding | `READINESS_REJECTED` / `not_applicable`, or sealed `READINESS_INVALID_RECORD` | `control_plane` |
| Governed external-input collection is valid and empty | no failure; applicable input invariant is `passed` | none |
| A governed source object changed after the sealed `S` | `CURRENT_READINESS` or `LAUNCH_REJECTED` / `READINESS_STALE` | the exact owning invariant for the changed object |
| Current external input bytes differ from the sealed binding | `CURRENT_READINESS` or `LAUNCH_REJECTED` / `READINESS_INPUT_MISMATCH` | `current_external_inputs` |
| Current external input is unavailable before current readiness | `CURRENT_READINESS` or `LAUNCH_REJECTED` / `READINESS_BLOCKED_INPUT_UNAVAILABLE` | `current_external_inputs` |
| Current readiness passed but an attempt-local immutable launch snapshot cannot be created or validated | `LAUNCH_REJECTED` / `EXECUTION_READY` | `launch_input_snapshots` |
| Shared control storage is unavailable or nonconformant after current readiness | `LAUNCH_REJECTED` / `EXECUTION_READY` | `control_storage` |
| Namespace authority, reservation precondition, or collision check fails before allocation | `LAUNCH_REJECTED` / `EXECUTION_READY` | `output_namespace` |
| Applicable mandatory smoke selector fails | `LAUNCH_REJECTED` / `EXECUTION_READY` | `launch_smoke` |
| Required second fetch cannot be completed while the first snapshot remains current | `LAUNCH_REJECTED` / `EXECUTION_READY` | `second_fetch` |
| Required second fetch resolves a different `H` | no receipt yet; discard the unresolved launch and restart current-readiness resolution from the new `H` | none |

The `launch_smoke` entry in those and all other `LAUNCH_REJECTED` vectors is
determined exactly as follows:

| Evaluation outcome | Canonical `launch_smoke` status |
| --- | --- |
| Failure at `git_authority`, `schema_registry`, or `canonical_readiness_record` | `not_evaluated` |
| `validation` passes with an empty selector collection and a later invariant fails | `not_applicable` |
| `validation` passes with a nonempty collection but an invariant before smoke fails | `not_evaluated` |
| `launch_smoke` is reached and any mandatory selector fails | `failed` |
| Every mandatory selector passes and `second_fetch` later fails | `passed` |
| The record-owned policy field is malformed or missing | `not_evaluated`; `canonical_readiness_record` fails |
| The governed policy schema definition is unavailable, malformed, or identity/digest inconsistent | `not_evaluated`; `schema_registry` fails |
| The structurally valid record binding refers to a governed policy artifact that is missing, fails its established schema, or has selectors, identity, or required results that cannot be reconstructed or cross-validated | `not_evaluated`; `validation` fails |

There is no rejection receipt merely for reaching a valid empty selector
collection; if all later checks succeed, launch continues and no failure
vector is produced. The table states the smoke entry when some governed first
failure does produce a receipt.

For a stale object, "exact owning invariant" is not discretionary: it is the
one Section 5.4 identifier corresponding to that record section or governed
artifact. If several stale facts are observed, the first in the class-specific
evaluation order is canonical. A failure before evaluator entry or during
canonical serialization follows Section 5.4 and has no receipt vector.

### 5.7 Safety and implementation consequences

The exact 27-identifier vocabulary and full vector make receipts bounded, deterministic,
outcome-free, and incapable of carrying caller-authored text. Phase 3C may
construct only `READINESS_REJECTED`. Current-readiness and launch receipt
branches are governed now but produced only in their later lifecycle phases.

V1.1 and its strict receipt schema must encode all branches, cross-field rules,
precedence, and applicability above. Python conformance validation must
reconstruct the first failed invariant and disposition rather than trust a
schema-valid claim.

## 6. Terminal `FAILED` decision

### 6.1 Stable classes and deterministic precedence

The exact canonical `failure_class` domain remains:

1. `infrastructure_failure` — governed evidence establishes that execution or
   durable-control infrastructure failed and ended terminalization;
2. `interruption` — the governed live owner or invoking process terminated or
   became unavailable before terminal authority, without a higher-precedence
   ambiguity or established infrastructure/control failure;
3. `ambiguous_state` — the authoritative control state is conflicting,
   multiply interpretable, or cannot be uniquely reconstructed; and
4. `validity_not_established` — the control state is coherent, but scientific
   `VALID` or `INVALID` terminal authority was not established and no higher-
   precedence cause applies.

Classification is based on normalized governed control facts, not raw
exception types. The exact precedence is:

1. `ambiguous_state` when authoritative control state is conflicting or
   indeterminate;
2. `validity_not_established` when premature outcome access occurred, because
   v1 Section 20 fixes that violation as `FAILED` and the scientific boundary
   can no longer establish a conformant valid or invalid result;
3. `infrastructure_failure` when unambiguous governed evidence establishes an
   infrastructure or shared-control failure as the cause preventing terminal
   authority;
4. `interruption` when an owner/process termination or disappearance prevented
   terminal authority and no preceding rule applies; and
5. `validity_not_established` for the remaining coherent case in which the
   required scientific or invalidity authority cannot be established.

The first matching rule is canonical. Process identifier, exception class,
message, traceback, OS/storage error code, signal, and crash location are
noncanonical diagnostics and cannot alter classification.

After class selection, exactly one `normalized_failure_fact` is selected by
the following class-local first-match order. These orders use governed facts
from one atomic control-history observation plus its bound governed control
artifacts; they never use a subjective "primary cause":

| Failure class | Exact fact precedence, first matching value wins |
| --- | --- |
| `ambiguous_state` | `conflicting_authoritative_control_records`; then `indeterminate_authoritative_control_state` |
| `infrastructure_failure` | `shared_control_storage_failure`; then `execution_infrastructure_failure` |
| `interruption` | `governed_owner_terminated`; then `governed_owner_unavailable` |
| `validity_not_established` | `premature_outcome_access`; then `terminal_scientific_authority_not_established` |

`governed_owner_terminated` requires governed evidence of termination;
unavailability without such evidence selects `governed_owner_unavailable`.
`shared_control_storage_failure` requires failure of the shared authority used
for durable control, even when that is also execution infrastructure.
Missing audit evidence, missing governing invalidity evidence, and failure to
complete either terminal-evidence procedure all select the one stable
`terminal_scientific_authority_not_established` fact. Their detailed rule or
artifact failure remains noncanonical conformance information. Competing
`VALID` and `INVALID` terminal claims are a control conflict and select
`ambiguous_state`. This smaller vocabulary prevents an implementation from
inventing an unauthoritative intended terminal target after owner loss.

### 6.2 Exact scenario mapping

The following mappings are normative. `original boundary` means the boundary
selected by Section 6.3, never the later recovery operation:

| Governed scenario | Class | Normalized fact | Boundary | Recovery representation |
| --- | --- | --- | --- | --- |
| Process dies after allocation but before `STARTED` | `interruption` | `governed_owner_terminated` | `post_allocation_pre_start` | original live owner: `not_recovery_generated`; later recovery retains this class/fact/boundary |
| Process dies after `STARTED` but before invocation | `interruption` | `governed_owner_terminated` | `post_start_pre_ranking_freeze` | same rule |
| Process dies during scientific/profile execution before ranking freeze | `interruption` | `governed_owner_terminated` | `post_start_pre_ranking_freeze` | same rule; v1 has no separate durable invocation state |
| Shared storage fails while terminal authority is being persisted, without a conflicting snapshot | `infrastructure_failure` | `shared_control_storage_failure` | `terminalization` | same rule |
| Storage failure leaves a conflicting or nonlinear control snapshot | `ambiguous_state` | `conflicting_authoritative_control_records` | earliest boundary at which the conflict is present | Section 6.4 conflicting-history rule |
| Unhandled exception terminates the owner and no infrastructure failure is established | `interruption` | `governed_owner_terminated` | boundary active when termination became durable | original or recovered as applicable |
| Owner disappears without proof of termination | `interruption` | `governed_owner_unavailable` | boundary active at the last coherent owner-controlled state | recovery required before terminalization |
| Audit evidence is incomplete or the required Experiment Audit Manifest is missing | `validity_not_established` | `terminal_scientific_authority_not_established` | `terminalization` | original or recovered as applicable |
| Governing invalidity evidence is missing or incomplete | `validity_not_established` | `terminal_scientific_authority_not_established` | `terminalization` | original or recovered as applicable |
| Coherent evidence can establish neither `VALID` nor `INVALID`, with no more specific fact | `validity_not_established` | `terminal_scientific_authority_not_established` | `terminalization` | original or recovered as applicable |
| Premature outcome access occurs | `validity_not_established` | `premature_outcome_access` | earliest governed boundary at which unauthorized access occurred | original or recovered as applicable |
| Recovery proves no live owner over a coherent history | class selected from the underlying governed event under Section 6.1 | fact selected by that class's precedence | underlying original boundary | `recovery_no_live_owner_established` |
| Recovery observes conflicting nonterminal history and no valid terminal candidate | `ambiguous_state` | `conflicting_authoritative_control_records` | earliest conflict boundary | `recovery_no_live_owner_established` only under Section 6.4's atomic fence-and-append rule |
| Recovery observes one or more conflicting structurally valid terminal candidates | no new terminal class may be asserted | not applicable because no new `FAILED` record is permitted | not applicable | attempt remains `INCOMPLETE`; canonical conflict status is derived from the control-history snapshot |
| Valid-looking artifacts exist but terminal validity authority was not established | class selected by global precedence | fact selected by class-local precedence: shared-control failure, owner termination/unavailability, then terminal-authority fallback | `terminalization` unless the selected fact was established earlier | original or recovered as applicable |
| Invalidity evidence exists but terminal invalidity authority was not established | class selected by global precedence | fact selected by the same class-local precedence | `terminalization` unless established earlier | original or recovered as applicable |

When several conditions overlap, the implementation first normalizes the
atomic control-history snapshot under Section 6.3, Section 6.1 selects the
class and then its class-local fact, Section 6.3 selects the boundary of that
selected fact, and Section 6.4 selects recovery mode. These ordered steps
produce one representation; later or lower-precedence diagnostics cannot
change it.

### 6.3 Embedded canonical failure-control evidence

Option A is selected. `FAILED` embeds one closed
`failure_control_evidence` object directly in both the terminal attempt-control
record and execution-control manifest. It has no separate stored identity or
byte digest: each enclosing object's domain-separated identity already binds
the complete nested bytes, and cross-object validation requires byte-for-byte
canonical equality. No failure-control-evidence schema object kind is added.

Every branch contains exactly these common fields:

- `control_history`, the closed atomic snapshot defined below;
- `failure_boundary`, one value selected under the exact rule below;
- `failure_class`, one of the four values in Section 6.1;
- `last_durable_control_state`, exactly `ALLOCATED` or `STARTED`, equal to the
  state established by the unique common prefix or `ALLOCATED` when that prefix
  contains no control record;
- `normalized_failure_fact`, selected by Section 6.1;
- `scientific_invalidity_established=false`; and
- `scientific_validity_established=false`.

Each class is a closed discriminated branch with this exact fact domain:

| `failure_class` | Exact `normalized_failure_fact` domain |
| --- | --- |
| `ambiguous_state` | `conflicting_authoritative_control_records`, `indeterminate_authoritative_control_state` |
| `infrastructure_failure` | `shared_control_storage_failure`, `execution_infrastructure_failure` |
| `interruption` | `governed_owner_terminated`, `governed_owner_unavailable` |
| `validity_not_established` | `premature_outcome_access`, `terminal_scientific_authority_not_established` |

The selected normalized fact and class must satisfy Sections 6.1–6.2. Raw
diagnostics, outcomes, scientific results, exception material, machine-local
paths, timestamps, credentials, and caller-defined strings are prohibited.

`failure_boundary` means the earliest governed lifecycle boundary at which the
selected normalized fact became durably established as preventing normal
completion. It does not mean where the terminal record was written. Its exact
ordered domain is:

1. `post_allocation_pre_start`;
2. `post_start_pre_ranking_freeze`;
3. `post_ranking_freeze_pre_authorization`;
4. `post_authorization_pre_terminal`; and
5. `terminalization`.

The boundary is reconstructed from the allocation/start records and the
governed ranking-freeze, authorization, and terminalization artifacts. V1 does
not require durable proof of the instant of scientific invocation, so death
after `STARTED` and scientific failure before ranking freeze intentionally
share one boundary. When the exact boundary cannot be uniquely distinguished,
the earliest value consistent with all governed observations is canonical. A
later recovery operation never changes this field; recovery is represented
only by `recovery_mode` and `no_live_owner_evidence`.

`control_history` contains exactly:

- `control_history_kind`, exactly `coherent` or `conflicting`;
- `common_prefix_record_identities`, the derived unique valid prefix in control
  chain order, possibly empty; and
- `observed_control_objects`, the complete atomic shared-control snapshot for
  the attempt before terminal append.

Each observed authority slot is one of two closed branches:

1. `validated_control_record`, containing exactly
   `object_kind=validated_control_record`, positive integer
   `authority_sequence`, positive integer `declared_control_sequence`,
   lowercase SHA-256 `control_record_identity`, and a closed
   `predecessor_control_record_identity` branch. The absent branch is exactly
   `{"status":"absent"}`. The known branch contains exactly `identity` plus
   `status=known`; or
2. `conflicting_control_slot`, containing exactly positive integer
   `authority_sequence`, `object_kind=conflicting_control_slot`, one
   `normalized_slot_fact`, and `validated_records`. Each validated-record entry
   contains exactly `declared_control_sequence`, `control_record_identity`, and
   the same closed predecessor branch as above; the array is sorted and unique
   by `control_record_identity`. The exact slot-fact branches are:
   - `malformed_only`: `validated_records` is empty and at least one malformed
     object exists;
   - `duplicate_valid_record`: `validated_records` contains exactly one entry
     and more than one copy of those exact valid bytes exists;
   - `multiple_valid_records`: `validated_records` contains at least two
     distinct valid identities and no malformed object exists; or
   - `valid_and_malformed`: `validated_records` is nonempty and at least one
     malformed object also exists.

The slot array is sorted by `authority_sequence` and unique by that value.
`authority_sequence` is assigned by the shared control authority and is
independent of a record's caller-declared sequence. The shared authority
normalizes every slot to exactly one branch. Exact malformed bytes, their
digests, counts, paths, and backend keys remain outside canonical evidence.
Schema-valid record identities and predecessor facts are retained because they
are governed control objects needed to reconstruct competing branches. Later
validation re-observes the slot and proves the normalized branch and every
retained valid identity. This prevents arbitrary malformed bytes or
multiplicity from becoming a canonical payload channel while preserving every
valid competing branch.

`coherent` is valid only when every slot is a valid control record and the
slots form exactly one linear predecessor chain with one root, unique
declared sequences that are consecutive from 1, and no duplicate or competing terminal. Its common prefix
is the complete chain. `conflicting` is valid only when the snapshot is not
such a chain because it contains a conflicting slot, multiple roots, a missing
or invalid predecessor, a missing or duplicate declared sequence, a fork, a
cycle, or competing terminal records.

For `conflicting`, reconstruction first identifies every entry participating
in the earliest conflict: every member of the first duplicate-declared-
sequence set, fork-successor set, competing-terminal set, multiple-root set, or
cycle, or the first conflicting slot or missing-predecessor entry. The conflict
frontier is the minimum `authority_sequence` among those participants. The
common prefix is the longest unique root-origin chain
of valid records that is an ancestor of every valid competing branch and whose
members sort strictly before that frontier. The common fork predecessor is
therefore retained while all competing successors are excluded. The prefix is
empty when there is no unique valid root, including multiple roots, a malformed
root position, or a rootless cycle.

Competing branches are not named by a caller: they are the maximal successor
paths derived from all retained validated entries, while malformed-only slots
are conflicting leaves identified only by their authority-assigned sequence
and normalized slot fact. Conflict types are evaluated in the fixed order just listed when
more than one type occurs at the same sequence. The stored prefix MUST equal independent
reconstruction. Binding the complete sorted snapshot, rather than one selected
branch, permits deterministic proof of duplicate sequences, nonlinear
histories, malformed objects, and conflicting terminal candidates without
pretending any competing branch is authoritative.

`normalized_failure_fact=conflicting_authoritative_control_records` requires
`control_history_kind=conflicting`. A `FAILED` object with that fact may be
created only by the Section 6.4 conflicting-history recovery operation. Every
other normalized fact, including `indeterminate_authoritative_control_state`,
requires `control_history_kind=coherent`; indeterminacy in that branch concerns
a governed authority fact outside the structurally unique control chain. No
`FAILED` evidence snapshot may contain a structurally valid terminal control
candidate. Its presence prohibits a new `FAILED` append and leaves terminal
status to ordinary unique-terminal validation or the conflicting-terminal
`INCOMPLETE` rule in Section 6.4.

### 6.4 Recovery is orthogonal and atomic

The exact `recovery_mode` domain is:

- `not_recovery_generated`; and
- `recovery_no_live_owner_established`.

`recovery_no_live_owner_established` is not a failure class. For
`not_recovery_generated`, recovery evidence is exactly `absent`. For
`recovery_no_live_owner_established`, the terminal record and manifest contain
the same closed `no_live_owner_evidence` object with exactly these fields in
canonical object-key order:

1. `allocation_authority_identity`;
2. `no_live_owner_established=true`;
3. `recovery_component_identity`;
4. `recovery_operation=atomic_compare_no_live_owner_and_append_failed`;
5. `recovery_policy_identity`.

The exact observed history is the sibling `failure_control_evidence.control_history`
object in the same enclosing terminal object; it is not duplicated in the
recovery branch. Both the terminal record and manifest bind the same complete
history bytes and the same no-live-owner evidence.

No standalone proof object is required. The canonical object binds the unique
authority instance, governed policy, governed recovery component, exact prior
chain, and operation. Operational conformance must prove that the governed
recovery component performed one atomic shared-control compare-and-append
operation that:

1. evaluated the bound recovery policy;
2. atomically enumerated and rehashed every object in the bound control-history
   snapshot;
3. established under the shared allocation/control authority that no live
   owner could still complete the attempt;
4. atomically prevented any live owner or competing recovery process from
   establishing a conflicting terminal state; and
5. appended/reserved exactly one recovery-generated `FAILED` terminal record
   together with its matching final control-manifest authority.

Schema validation proves the closed shape. Python validation proves identity,
sequence, component/policy, and cross-object equality. The shared authority's
atomic operation proves the transient no-live-owner fact. Raw leases,
timestamps, host/process observations, and backend diagnostics remain outside
canonical material.

For a coherent history, the atomic operation requires the snapshot to remain
the same unique chain through compare-and-append. The recovery terminal
record's predecessor is the last record in that chain, or the exact absent
branch when the chain is empty. For a conflicting history,
recovery MAY append one attempt-level `FAILED` record without choosing or
merging a branch only when the same atomic operation proves all of the
following: the complete conflicting snapshot is unchanged; no structurally
valid terminal control candidate exists in any branch; no live owner remains;
the authority fences every prior branch from further append; and no competing
recovery writer has succeeded. The recovery record refers to the allocation
and complete embedded conflict snapshot rather than claiming a predecessor
from one branch; its predecessor binding is exactly the absent branch and this
is permitted only for the conflicting-history recovery branch.

If a conflicting snapshot contains any structurally valid terminal candidate,
if the control store is partitioned or unavailable, if enumeration is
incomplete, or if the snapshot changes during the operation, recovery MUST NOT
append. Under the conflicting-snapshot condition the attempt remains
`INCOMPLETE`, no branch is selected or repaired, and status derives a
nonterminal `INCOMPLETE` result while reporting the deterministic conflict view
when the shared store can be atomically observed. A coherent unique valid
terminal record follows ordinary terminal validation and is outside recovery.
When no complete stable snapshot can be obtained, the preexisting allocation
or start history likewise remains `INCOMPLETE` and no conflict view or terminal
object is fabricated.
Conflicting terminal candidates may therefore remain permanently
`INCOMPLETE`; v1.1 provides no destructive repair or scientific reinterpretation.
The immutable shared-control objects remain the audit record, and status may
reconstruct the same deterministic conflict view on demand; that derived view
is not a new stored control object or authority.
An original owner racing recovery, or two recovery writers racing each other,
is resolved only by the one shared atomic fence-and-append operation: at most
one writer succeeds and every loser observes failure without creating a
terminal object.

### 6.5 Scientific evidence eligibility versus terminal authority

Scientific evidence eligibility and terminal control authority are distinct.

`VALID` requires all of the following:

1. the required Experiment Audit Manifest and scientific evidence exist;
2. a governed live owner canonically reconstructs and successfully validates
   them under the bound protocol and Research Execution Specification; and
3. that same live owner atomically and durably establishes the unique `VALID`
   terminal control record and matching final execution-control manifest under
   shared control authority.

`INVALID` analogously requires explicit immutable governing invalidity
evidence, every audit/conformance manifest required for invalid execution,
successful governed reconstruction and validation by the live owner, and the
same atomic durable terminal-control establishment.

Evidence presence or content eligibility is necessary where v1 requires it,
but never sufficient terminal authority. A file, artifact, or manifest that
exists when terminalization fails cannot establish `VALID` or `INVALID` by
itself. Recovery is authorized only to establish `FAILED`; it MUST NOT
reinterpret scientific artifacts or governing invalidity evidence to upgrade
an attempt to `VALID` or `INVALID`.

If eligible evidence exists but a storage failure, owner interruption, or
other governed fact prevents atomic terminal authority, classification follows
Sections 6.1–6.3. `FAILED` therefore represents that neither terminal validity
nor terminal invalidity was established, even when nonauthoritative or
unterminalized scientific artifacts remain present.

### 6.6 Control-record and manifest equality

For `FAILED`, the unique terminal attempt-control record and final execution-
control manifest MUST contain canonically identical values for:

- final control disposition;
- the complete embedded `failure_control_evidence` object;
- recovery mode; and
- the complete `no_live_owner_evidence` object or exact `absent` value.

Both objects independently bind the attempt, allocation receipt, readiness,
launch authority, source authority, input snapshots, and profile as v1 already
requires. Cross-object validation rejects any mismatch. The atomic terminal
operation must prevent a partial record/manifest pair from becoming terminal
authority. `INCOMPLETE` remains derived and nonterminal and carries no terminal
evidence.

### 6.7 Compatibility and consequences

This model gives exact canonical meaning to Sections 4.4, 12, 16.2, and the
premature-outcome-access regression without freezing OS exception taxonomies.
It preserves the scientific/control distinction and recovery prohibition.

V1.1 schemas and tests must use closed state-specific branches for `STARTED`,
`VALID`, `INVALID`, `FAILED`, and manifest `INCOMPLETE`; enforce the precedence
and scenario table; validate the embedded evidence branches; cover both
recovery modes and atomic recovery semantics; reject cross-state evidence; and
prohibit diagnostic payloads.

## 7. Official and reproduction attempt-support decision

### 7.1 Structural contract rule

A reusable attempt-authority contract has `supported_attempt_kinds` equal to
exactly one of these canonical arrays:

1. `["official"]`
2. `["official","reproduction"]`
3. `["reproduction"]`

The canonical element order is `official` before `reproduction`; elements are
unique and the array is nonempty. A reproduction-only contract is a valid
governed object.

### 7.2 Cross-contract suitability rule

Attempt-kind suitability is not a reusable-schema invariant. It is a
readiness/launch cross-contract invariant:

- an official readiness candidate and every official launch MUST resolve one
  attempt authority whose supported set contains `official`; and
- a prospective readiness-v1 reproduction MUST resolve one attempt authority
  whose supported set contains `reproduction`.

The selected kind must equal the attempt kind in namespace material, attempt
identity material, the allocation receipt, and every control object. A
reproduction can never be relabeled official. Phase 3C validates official
support for a candidate but does not allocate either kind.

This placement preserves the reusable contract while satisfying Sections 3.8,
11, and 17 at the point where an intended attempt kind is known.

## 8. Schema-registry decision

### 8.1 Final count and new object

The clarified complete readiness-v1.1 registry contains exactly **29** schema
object kinds. This list is governance authority and does not depend on the
uncommitted Slice-1 implementation.

The Phase 2 base contains exactly these six kinds in canonical object-kind
order:

1. `implementation-binding`
2. `launch-authority-snapshot`
3. `readiness-record`
4. `readiness-test-policy`
5. `repository-authority`
6. `source-scope`

Phase 3A adds exactly these four kinds:

1. `adapter-declaration`
2. `adapter-registry`
3. `offline-artifact-manifest`
4. `runtime-contract`

The resulting Phase 3A set is exactly ten: the Phase 2 six plus those four.

Phase 3B adds exactly these ten kinds:

1. `artifact-declaration-evidence`
2. `dataset-validation-evidence`
3. `evidence-preparation`
4. `evidence-preparation-policy`
5. `immutable-input-snapshot`
6. `outcome-blind-projection-evidence`
7. `population-accounting-evidence`
8. `profile-conformance-evidence`
9. `readiness-test-evidence`
10. `replay-evidence`

The resulting Phase 3B set is exactly twenty: the Phase 3A ten plus those ten.

Clarified readiness-v1.1 adds exactly these nine kinds:

1. `attempt-allocation`
2. `attempt-authority-contract`
3. `attempt-control-record`
4. `attempt-identity-material`
5. `execution-control-manifest`
6. `outcome-authorization`
7. `output-namespace-identity-material`
8. `profile-contract`
9. `readiness-failure-receipt`

The complete 29-kind registry, in canonical object-kind order, is therefore:

1. `adapter-declaration`
2. `adapter-registry`
3. `artifact-declaration-evidence`
4. `attempt-allocation`
5. `attempt-authority-contract`
6. `attempt-control-record`
7. `attempt-identity-material`
8. `dataset-validation-evidence`
9. `evidence-preparation`
10. `evidence-preparation-policy`
11. `execution-control-manifest`
12. `implementation-binding`
13. `immutable-input-snapshot`
14. `launch-authority-snapshot`
15. `offline-artifact-manifest`
16. `outcome-authorization`
17. `outcome-blind-projection-evidence`
18. `output-namespace-identity-material`
19. `population-accounting-evidence`
20. `profile-conformance-evidence`
21. `profile-contract`
22. `readiness-failure-receipt`
23. `readiness-record`
24. `readiness-test-evidence`
25. `readiness-test-policy`
26. `replay-evidence`
27. `repository-authority`
28. `runtime-contract`
29. `source-scope`

The sole new kind created by this clarification, rather than the earlier
Phase-3C schema analysis, is:

```text
output-namespace-identity-material
```

Its exact schema identifier is:

```text
orev3://schemas/execution-readiness/v1/output-namespace-identity-material
```

Its exact normative path is:

```text
src/orev3/execution/schemas/v1/output-namespace-identity-material.schema.json
```

Its stable schema-policy identifier is:

```text
output-namespace-identity-material-v1
```

The schema governs only the seven-field identity material in Section 4.4. Its
existence does not create an ordinal, attempt, receipt, path, directory,
namespace reservation, allocation authority, or execution capability during
Phase 3C.

### 8.2 No other new schema kind

No separate failure-code registry is added. The 27 stable invariants are a
closed enum owned by the failure-receipt schema and specification revision.

No standalone failure-control or recovery-evidence schema is added. The
attempt-control-record and execution-control-manifest schemas own the exact
closed embedded structures in Section 6, while the bound authority and policy
own the operational proofs.

No namespace-realization schema is added. Realization is later operational
behavior governed by the attempt-authority contract, output policy, allocation
receipt, and cross-object validation. The realized path is not canonical
readiness identity material.

The new schema is necessary because its exact fields determine a new domain-
separated identity and independent implementations must reconstruct identical
bytes. Prose alone previously left that identity undefined.

## 9. Specification-revision decision

### 9.1 Immutable new revision

The clarification must be incorporated into one consolidated immutable file:

```text
docs/research/specifications/experiment-execution-readiness-v1.1.md
```

with internal revision:

```text
experiment-execution-readiness-v1.1
```

The existing v1 file and digest remain immutable. V1.1 is additive and
clarifying: it incorporates the complete v1 text plus the exact decisions in
this document so a reader does not need two documents to implement the
contract.

### 9.2 Identity domains and bindings

All existing v1 identity domain lines remain byte-for-byte unchanged,
including:

```text
orev3:experiment-execution-readiness:v1\n
```

The v1.1 readiness record is nevertheless distinct because its required
`readiness_specification` section binds revision, path, bytes, SHA-256, and Git
blob identity for the v1.1 document. Changing those governed bytes changes the
record and readiness identity under the unchanged domain.

V1.1 adds exactly two domain lines:

```text
orev3:experiment-attempt-allocation-authority:v1\n
orev3:experiment-output-namespace:v1\n
```

No old identity is recomputed or relabeled. New Phase 3C source commits must
bind the v1.1 path, revision, exact future digest, and Git blob at `S`. No
digest may be guessed before the final v1.1 bytes are frozen.

## 10. Compatibility analysis

### 10.1 Phase 2, Phase 3A, and Phase 3B

The frozen implementation results remain historically valid within their
implemented boundaries:

- Phase 2: `GIT_AUTHORITY_VALIDATED`;
- Phase 3A: `PREPARATION_ENVIRONMENT_VALIDATED`; and
- Phase 3B: internal/non-authoritative
  `EVIDENCE_PREPARATION_VALIDATED`.

This decision does not reinterpret those results or claim they were produced
under v1.1. Their frozen commits remain evidence of the behavior reviewed at
their governing source and specification digest.

Before Phase 3C can mint `READINESS_VALIDATED`, a future source commit
containing v1.1 and the corrected schema foundation must reconstruct fresh
Phase 2, Phase 3A, and Phase 3B evidence under that `S`. Existing Phase 2/3A/3B
authority, hermeticity, outcome isolation, and evidence semantics require no
architectural redesign. Bounded specification-path/revision/digest and final
schema-registry bindings must be updated for the new prospective source.

### 10.2 Historical research

Experiments 1–4 and Findings 001–006 remain governed by their historical
protocols, specifications, source bindings, manifests, and execution histories.
They are not migrated, reinterpreted, or retrospectively made readiness-v1 or
v1.1 conformant.

### 10.3 Phase 3B handoff

The Phase 3B handoff remains an immutable historical navigation document. It
must not be edited to make v1.1 appear to have governed work that preceded it.
A later continuation checkpoint may cite this approved decision, the frozen
v1.1 commit/digest, and the resulting Phase 3C Slice-1 state.

## 11. Phase 3C boundary preservation

This decision does not change the accepted Phase 3C boundary:

```text
fresh Phase-2 authority + automatic S
  -> detached Phase 3A/3B evidence
  -> complete normalized evidence retained inside detached S
  -> deterministic canonical readiness-record candidate
  -> independent schema/Python/Git/cross-evidence validation
  -> exact canonical candidate bytes + readiness_identity
  -> READINESS_VALIDATED
```

or, on any unmet prerequisite:

```text
canonical outcome-free READINESS_REJECTED
```

This outcome assumes the canonical receipt serializer is available. A
`CANONICAL_RECEIPT_UNAVAILABLE` control-plane abort under Section 5.4 creates
neither branch and advances no lifecycle state; it cannot be treated as
`READINESS_VALIDATED` or as a schema-valid rejection receipt.

Phase 3C still ends before candidate persistence, canonical readiness-path
materialization, seal `R`, current-readiness resolution, launch-authority and
input snapshots, launch smoke, second-fetch launch checks, attempt allocation,
namespace realization, `STARTED` or terminal control records, ranking freeze,
outcome authorization, evaluation, execution, or the official runbook.

The namespace, current-readiness, launch, allocation, terminal, authorization,
and manifest schemas govern future objects. Defining them does not authorize
Phase 3C to create those objects.

## 12. Exact normative changes for v1.1

The v1.1 draft must make these bounded changes:

| V1 section | Required clarification |
| --- | --- |
| Status and compatibility | Set revision to `experiment-execution-readiness-v1.1`; state that v1 remains immutable and historical. |
| 3.8 | Define the unique allocation-authority instance identity and exact identifier grammar, preserve ledger continuity across backend migration, distinguish it from reusable allocator-contract identity, distinguish pre-attempt namespace identity from post-attempt realization, and retain one atomic allocation transaction. |
| 4.3, 10, 13 | Add the three receipt classes, exact current-readiness disposition branching, and the outcome-free bounded receipt model. |
| 4.4 and 12 | Add deterministic class and same-class fact precedence, durable boundary selection, the complete coherent/conflicting control-history snapshot, embedded normalized evidence, orthogonal recovery modes, separate coherent/conflicting recovery rules, live-owner terminal-authority rules, atomic recovery, and control-record/manifest equality. |
| 6.2 | Require the 29-schema registry and the new namespace-identity-material schema binding. |
| 6.3 | Apply existing canonical JSON rules to the fixed receipt status vector and new namespace material. |
| 6.5 | Add the allocation-authority and output-namespace domains, their exact material, and the cycle-free dependency order. |
| 11.3 | State the logical identity order inside atomic allocation and retain all existing attempt/receipt authority bindings. |
| 13 | Define the exact receipt common fields, branches, 27 identifiers, status meanings, order, stage applicability, progressive governed conditional applicability, evaluator-entry and serialization availability boundary, active-invariant machinery-failure normalization, exact registry/record ownership, and first-failure rule. |
| 15.2 | Require an exact sorted/unique `launch_smoke_selectors` collection whose emptiness alone governs smoke applicability. |
| 16.1 | State that realization maps the already-derived attempt identity but does not participate in namespace identity. |
| 16.2 | Distinguish scientific-evidence eligibility from live-owner terminal authority; define state-specific embedded `FAILED` evidence and exact equality with the terminal control record. |
| 17 | Place attempt-kind support in cross-contract validation and freeze the canonical supported-kind subsets. |
| 20–21 | Add reconstruction, cycle, receipt-vocabulary, terminal-class, recovery, attempt-kind, and no-payload regressions. |

No other v1 requirement is changed.

## 13. Implementation consequences

After this decision and v1.1 are approved and frozen, Phase 3C Slice 1 must:

1. add the strict `output-namespace-identity-material` schema;
2. change the final registry target from 28 to 29 without changing the frozen
   Phase 2/3A/3B 6/10/20 policies;
3. encode the allocation-authority identity material as a closed definition
   in `attempt-authority-contract` and replace the invented namespace policy
   with the exact Section 4 namespace material and identifier grammar;
4. replace invented failure categories with the exact receipt branches,
   dispositions, 27-identifier vector, stage and progressive conditional
   applicability rules, registry/record/policy ownership, and canonical-receipt
   availability boundary;
5. replace incomplete terminal `FAILED` branches with the four classes, two
   recovery modes, embedded control-history graph and evidence branches,
   class/fact/boundary precedence, live-owner terminalization, and coherent and
   conflicting atomic recovery rules;
6. permit all three structurally valid supported-attempt-kind arrays and add
   later cross-contract validation for requested-kind suitability;
7. add the required sorted/unique `launch_smoke_selectors` declaration to the
   future v1.1 readiness-test policy and its governed configuration;
8. update future readiness-specification constants and bindings to the final
   v1.1 path, revision, bytes, digest, and Git blob only after those bytes
   exist; and
9. retain fail-closed production behavior when genuine orchestrator,
   allocator, outcome-gate, adapter, or policy prerequisites are absent.

No placeholder implementation or SHA-shaped value may satisfy semantic
authority. Slice 1 remains schema foundation only.

## 14. Test consequences

The v1.1 and Slice-1 regression suites must establish at minimum:

- exact reconstruction of allocation-authority instance identity and proof
  that distinct authority instances cannot collide, every rejected identifier
  spelling fails, and backend migration cannot fork or reset the ledger;
- exact reconstruction of the seven-field namespace material and domain;
- the acyclic order namespace identity → attempt identity → receipt identity;
- identical namespace identity across conforming executors;
- realized namespace cross-binding and no-overwrite collision behavior in the
  later allocator slice;
- all three receipt classes and every permitted current-readiness disposition;
- rejection of cross-class disposition combinations;
- exact 27-entry check order, evaluator-entry activation, active-invariant
  internal-failure normalization, no fabricated pre-entry or serialization-
  failure receipt, exact registry/record ownership, one failed invariant,
  fixed status meanings, stage applicability, progressive smoke-selector
  applicability, every early/policy/empty/nonempty smoke status branch,
  empty-input passes,
  unknown identifiers, oversized strings, outcome sentinels, and encoded
  payload attempts;
- all four `FAILED` classes, complete class/fact/boundary scenario mapping and
  precedence, coherent and conflicting graph canonicalization, malformed,
  duplicate-sequence, fork, cycle, and competing-terminal histories, every
  embedded evidence branch, both recovery modes, coherent and conflicting
  atomic no-live-owner compare-and-append, necessary-versus-sufficient terminal
  authority, and control-record/manifest equality;
- rejection of raw diagnostics and cross-state scientific evidence;
- all three supported-attempt-kind arrays and rejection of empty, duplicate,
  reordered, or unknown arrays;
- official and reproduction suitability at the later cross-contract layer;
- exact 6/10/20/29 registry counts, unique kinds/IDs/paths, and real schema
  bytes/digests; and
- preservation of Phase 2, Phase 3A, Phase 3B, outcome isolation, and the sole
  future `READINESS_VALIDATED` mint boundary.

## 15. Historical-validity statement

This clarification is prospective. It does not repair or invalidate an older
record, execution, manifest, finding, checkpoint, or evidence object. An
artifact remains governed by the exact immutable specification revision and
digest it originally bound. A later revision cannot silently alter that
meaning.

## 16. Explicit non-goals

This decision does not:

- edit or supersede the frozen v1 bytes in place;
- draft the v1.1 specification;
- implement or authorize Phase 3C;
- construct or persist a readiness candidate or failure receipt;
- create a canonical readiness path or seal `R`;
- resolve current readiness or launch authority;
- implement an orchestrator, allocator, outcome gate, adapter, or recovery
  service;
- allocate an attempt, ordinal, receipt, or output namespace;
- create `STARTED`, terminal, authorization, or control-manifest objects;
- rank, evaluate, authorize outcomes, or execute an experiment;
- revise scientific methodology or historical research; or
- authorize mining, wallet, transaction, live-capital, or real-SOL behavior.

## 17. Open questions

None. The choices required to draft v1.1 are fixed by this decision. Review may
reject a choice, but implementation must not substitute a different choice
without a revised governance decision.
