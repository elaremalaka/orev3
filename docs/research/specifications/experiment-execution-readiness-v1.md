# Experiment Execution Readiness Specification v1

## Status

- Type: Repository-wide prospective pre-execution control-plane specification
- Revision: `experiment-execution-readiness-v1`
- State: Proposed normative foundation
- Application: Future official experiments only
- Compatibility: Layered above existing Research Execution Specifications

This specification defines when a future experiment is eligible to begin an
official execution. It does not replace or modify the
[RQ-003 Research Execution Specification v1](rq003-research-execution-specification.md)
or the
[RQ-003 Research Execution Specification v2](rq003-research-execution-specification-v2.md).
Those specifications continue to govern execution-time provenance, Replay,
artifact, outcome-boundary, conformance, and manifest behavior for experiments
that bind them.

The key words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** in
this document are normative requirements. Text explicitly labeled as
"Rationale," "Example," or "Historical motivation" is explanatory and is not
an additional requirement.

## 1. Purpose and scope

This specification defines a fail-closed readiness lifecycle in front of the
scientific execution lifecycle. Its purpose is to make official execution
structurally unreachable until the repository contains one coherent,
remote-backed, reproducible experiment source state and a reviewed readiness
seal for that state.

This specification owns:

- the prospective readiness lifecycle and its transitions;
- source-candidate selection and remote Git authority;
- readiness validation in clean detached source state;
- the canonical readiness record and readiness identity;
- the readiness seal and current-readiness reconstruction;
- staleness and launch rejection;
- official and reproduction attempt classification;
- pre-execution outcome-access policy;
- readiness and launch failure receipts; and
- readiness conformance requirements.

It does not select or modify an experiment's scientific question, hypothesis,
measurement, Feature Set, ranking, comparator, cohort, exclusion, metric,
uncertainty method, interpretation rule, or validity criterion.

The normative authority chain is:

```text
coherent pushed source commit S
  -> isolated readiness validation
  -> canonical readiness record
  -> reviewed and pushed readiness seal commit R
  -> official executor resolves R
  -> clean checkout of S
  -> profile-specific execution
  -> readiness-v1 execution-control manifest plus existing Experiment Audit Manifest
  -> validity disposition
  -> frozen finding
```

Every arrow in this chain MUST be validated. A later stage MUST NOT repair,
infer, or silently substitute a missing earlier stage.

## 2. Historical motivation and prospective application

### 2.1 Historical motivation

Experiment 2D implementation commit
`3ba070ba3c2173d63df690054c4c91957b640db9`, Experiment 3 implementation
commit `d06734d715ff85aa6e35d373b6bc6d8854425615`, and Experiment 4
implementation commit `ca1e3f722a246b70d61f1b6705a8bbc2806ad416` each contained an
implementation and protocol digest binding but did not contain the protocol
document required by the implementation's governed source scopes. Their
execution preflights correctly failed. The corresponding coherent source
states were established only after protocol commits
`b09400d723d7bb9cd72efcf2b45c986eef000bb8`,
`7f0418fbefa78de883d9e2590f7f6de031989811`, and
`c42e2ef2727bcf86c1cad87d42b065b44c0e5ffd`.

Experiment 4 also demonstrated that a previously copied source SHA could be
reused after a coherent protocol freeze existed. Immutable-source validation
again correctly failed, but a manual readiness audit was required to identify
the correct state.

These events motivate the readiness control plane. They do not alter the
historical validity, authority, attempt classification, artifacts, or findings
of Experiments 1 through 4.

### 2.2 Prospective application

This specification MUST apply prospectively to every future official
experiment after its implementation is approved and adopted. Experiments 1
through 4 MUST remain governed by their historical protocols, source bindings,
Research Execution Specifications, and recorded execution histories.

No retrospective readiness record MAY claim or imply that this lifecycle
governed a historical experiment when it did not.

## 3. Terminology and authority objects

### 3.1 Source commit `S`

The **source commit**, denoted `S`, is the exact full Git commit identity whose
tree is proposed as the immutable source of one official experiment execution.

`S` MUST contain mutually coherent versions of:

1. the complete governing experiment protocol;
2. the experiment implementation or registered execution adapter;
3. the implementation's protocol revision and exact protocol-byte digest
   binding;
4. the applicable Research Execution Specification and its binding;
5. the declared execution profile and profile binding;
6. every governed source scope;
7. the tests required by the readiness contract;
8. configuration declarations needed to reconstruct readiness;
9. dataset declarations and externally owned input bindings; and
10. artifact and attempt-output declarations needed before launch.

Every tracked item used to prepare or execute the experiment MUST be obtainable
from `S`. An uncommitted file, ignored generated file, command transcript,
operator statement, later commit, or working-tree substitution MUST NOT supply
tracked execution source missing from `S`.

Externally stored datasets and generated artifacts MUST NOT be committed merely
to satisfy this requirement. They MUST instead be bound by the external-input
contracts in Section 9.

### 3.2 Readiness validation

**Readiness validation** is the isolated, outcome-policy-conformant evaluation
of `S` and its declared external inputs against every invariant in this
specification. It MUST execute from a clean detached checkout of `S` and MUST
produce either:

- a canonical readiness record candidate; or
- a readiness rejection receipt identifying the exact failed invariant.

Readiness validation MUST NOT execute the governed scientific experiment.

### 3.3 Readiness seal commit `R`

The **readiness seal commit**, denoted `R`, is a later full Git commit identity
that adds the reviewed canonical readiness record binding `S`.

`R` MUST:

- have `S` as an ancestor;
- be a single-parent commit;
- add or update exactly the experiment's canonical readiness-record path
  relative to its sole parent;
- contain no change to the governed source scopes bound by the record;
- preserve the reviewed readiness-record bytes exactly; and
- be pushed to the approved remote branch before current execution readiness
  can be established.

The readiness identity MUST NOT contain `R`, the Git object identity of `R`, or
any other value whose construction depends on committing the readiness record.
This prohibition prevents a self-referential identity.

`R` establishes the immutable historical fact that the readiness record was
sealed. It does not permanently assert that the experiment remains currently
executable.

`R` is not supplied by an operator. Given one freshly fetched approved remote
head `H`, the resolver MUST derive `R` as follows:

1. read the exact blob at the experiment's canonical readiness-record path in
   `H`;
2. traverse the first-parent ancestry of `H` from newest to oldest;
3. locate the unique most-recent commit at which that canonical path changed
   from a different or absent blob to the exact current blob;
4. require that commit to have exactly one parent and to change no path other
   than the canonical readiness-record path relative to that parent; and
5. require `S` to be an ancestor of that commit and that commit to be an
   ancestor of `H` under the same first-parent authority history.

That unique commit is `R`. If the current blob, first-parent history, commit
shape, path-only diff, or ancestry cannot establish exactly one `R`, current
readiness MUST be `READINESS_AMBIGUOUS` or `READINESS_ORPHANED` according to
Section 10 and official launch MUST fail closed.

An older record does not regain current authority merely because its bytes
remain in Git history. Reintroducing earlier record bytes requires a new,
reviewed, path-only seal commit; that new commit becomes a distinct `R` even
when the readiness identity is unchanged. Attempt authority binds `R`, so the
two seals cannot claim the same launch authority.

### 3.4 Sealed readiness and current readiness

**Sealed readiness** is a historical property of a readiness record committed
at `R`. It MUST remain reconstructable from repository history.

**Current readiness** is a derived property reconstructed at readiness-status
or launch time from:

- the sealed canonical readiness record;
- the current approved remote branch;
- ancestry and reachability;
- current governed-source relationships;
- current availability and exact identity of required external inputs; and
- every freshness and ambiguity rule in this specification.

No mutable field such as `currently_ready: true` MAY be authoritative inside
the canonical readiness record. The literal lifecycle state
`EXECUTION_READY` MUST be derived, never trusted as stored mutable state.

### 3.5 Approved Git authority

The **repository authority identity** is a stable, repository-governed
identifier for the approved Git repository. It is independent of local remote
aliases such as `origin`. Repository governance MUST map that identity to one
or more allowlisted canonical fetch endpoints.

The **approved branch ref** is one full Git ref name, such as
`refs/heads/research/post-v1`. A short branch name is not sufficient authority.

The readiness record MUST bind the repository authority identity and full
approved branch ref. At runtime, a local remote alias MAY select an endpoint,
but the resolver MUST prove that the alias maps to an endpoint allowlisted for
the bound repository authority. Machine-local repository paths, aliases,
credentials, and credential locations MUST NOT participate in readiness
identity.

### 3.6 Launch-authority snapshot

The **launch-authority snapshot** is the immutable authority resolved from one
successful fresh fetch immediately before durable attempt allocation. It MUST
contain:

- launch-authority schema version;
- repository authority identity;
- full approved branch ref;
- the exact fetched remote-head commit `H`;
- canonical readiness-record path;
- readiness-record Git blob identity;
- derived seal commit `R`;
- readiness identity; and
- source commit `S`.

The snapshot MUST have its own domain-separated canonical identity. All
critical launch checks MUST operate against one pinned snapshot. If a required
second fetch before durable allocation resolves a different `H`, the executor
MUST discard the unresolved launch attempt and restart authority resolution
from the new head. After an immutable allocation receipt is persisted, later
remote movement MUST NOT mutate or invalidate the running attempt; it affects
only later launch resolutions.

### 3.7 Governed source scopes

**Governed source scopes** are the ordered, nonempty, nonoverlapping or
unambiguously nested repository-relative paths whose committed Git objects
constitute the tracked source authority for the experiment.

At minimum, they MUST cover the protocol, bound execution specification,
this readiness specification, readiness validator, official orchestrator,
adapter registry, selected experiment adapter or implementation,
repository-owned attempt-allocation client and contract implementation,
outcome gate, canonical serialization implementation, all shared executing
source selected by repository policy, runtime/dependency manifests, mandatory
readiness-test policy, and required readiness tests.

Under the repository layout governed by v1, the complete `src/orev3/` tree
MUST be a governed scope. Protocols, specifications, tests, dependency
manifests, and policy files outside that tree MUST be additional governed
scopes. A later repository layout MAY change this rule only through a new
readiness-specification revision; an adapter cannot narrow it. Every imported
project module and repository-owned executable dependency MUST therefore fall
inside a recorded governed scope.

Set-like governed source scopes MUST be sorted by normalized repository path
and MUST have unique normalized paths. A broader scope MAY contain a narrower
declared scope only when the schema explicitly marks that nesting and assigns
one unambiguous object-identity role to each; otherwise overlap MUST fail
closed.

### 3.8 Attempt-allocation authority

Each experiment under one repository/research authority MUST resolve exactly
one configured **attempt-allocation authority** visible to every official
executor authorized for that research authority. It MUST provide atomic
compare-and-create semantics for permanent kind-specific ordinals, attempt
identities, allocation receipts, and output-namespace identities.

The allocation authority MAY be implemented with a shared filesystem,
content-addressed object store, transactional service, or another mechanism.
This specification does not require a database. If no configured mechanism can
provide the required cross-process and cross-machine atomicity, official
execution MUST remain unavailable.

## 4. Canonical lifecycle

### 4.1 Lifecycle states

The prospective lifecycle has these normative states:

| State | Meaning |
| --- | --- |
| `DRAFT` | One or more governed protocol, implementation, binding, test, or configuration elements MAY still change. |
| `SOURCE_CANDIDATE` | One exact pushed commit `S` has been selected for readiness validation. |
| `READINESS_VALIDATED` | `S` passed isolated readiness validation and produced a canonical readiness-record candidate, but the record is not yet established as a pushed seal. |
| `EXECUTION_READY` | A pushed seal `R` and all current derived eligibility checks establish that official execution MAY begin. |
| `EXECUTION_STARTED` | An immutable allocation receipt and immutable `STARTED` control record exist; the control plane has durably committed to attempt profile-specific invocation. This state does not prove that experiment code executed. |
| `EXECUTION_VALID` | The execution completed and was declared valid under its governing protocol and Research Execution Specification. |
| `EXECUTION_INVALID` | The execution began but a governing scientific or execution-conformance rule declared it invalid. |
| `FINDING_FROZEN` | A reviewed finding has been frozen as the scientific record of the authoritative result or disposition. |

`PROTOCOL_FROZEN` and `IMPLEMENTED` are readiness predicates, not lifecycle
states. Development MAY produce the protocol and implementation in either
order, but no order can bypass the complete readiness invariant. Repository
governance SHOULD freeze scientific intent before any governed outcome access.

### 4.2 Allowed transitions

The only normal forward transitions are:

```text
DRAFT
  -> SOURCE_CANDIDATE
  -> READINESS_VALIDATED
  -> EXECUTION_READY
  -> EXECUTION_STARTED
  -> EXECUTION_VALID | EXECUTION_INVALID
  -> FINDING_FROZEN
```

`FINDING_FROZEN` MAY follow either valid or invalid execution when the governing
research process requires a frozen invalidity record. A scientific finding
MUST NOT represent an invalid execution as valid evidence.

If `S` changes before sealing, the candidate MUST return to `DRAFT` or a new
`SOURCE_CANDIDATE`. If a sealed record becomes stale, the historical seal
remains, but current state MUST cease to be `EXECUTION_READY`. A changed source
requires a new `S`, readiness validation, and `R`.

### 4.3 Attempt dispositions that are not lifecycle states

The following are attempt dispositions, not scientific lifecycle states:

- `READINESS_REJECTED`: readiness validation failed before a readiness record
  was eligible for sealing;
- `LAUNCH_REJECTED`: a sealed record could not establish current readiness at
  official-launch time;
- `EXECUTION_FAILED`: execution started but infrastructure terminated before
  the governing system could establish scientific validity or invalidity.

These dispositions MUST NOT be represented as positive, negative,
inconclusive, or otherwise interpretable scientific evidence.

### 4.4 Attempt control states

Every allocated official or reproduction attempt has an append-only control
chain with these durable states:

| Control state | Meaning |
| --- | --- |
| `ALLOCATED` | The immutable allocation receipt exists; the ordinal and namespace are permanently consumed; experiment code has not necessarily started. |
| `STARTED` | An immutable start record binds the allocation receipt and durably commits the control plane to attempt profile-specific invocation immediately afterward. It does not claim or prove that experiment code executed. |
| `VALID` | Explicit protocol and execution-conformance evidence establishes a scientifically valid completed execution. |
| `INVALID` | Explicit protocol or execution-conformance evidence establishes scientific invalidity. |
| `FAILED` | Infrastructure failure, interruption, ambiguous state, or inability to establish `VALID` or `INVALID` ended the attempt. |

`INCOMPLETE` is a derived nonterminal disposition: an allocation or start
record exists but no unique valid terminal control record exists. Absence of a
terminal record MUST NOT imply `INVALID`, `FAILED`, or successful completion.
Recovery MAY append exactly one `FAILED` terminal record after it establishes
that no live owner can complete the attempt. Recovery MUST NOT modify, resume,
merge, or reinterpret the attempt's scientific artifacts.

## 5. The `EXECUTION_READY` invariant

An experiment is `EXECUTION_READY` if and only if one fresh authority
resolution establishes all requirements below. Any unknown, missing,
unsupported, inconsistent, noncanonical, unavailable, duplicated, or
ambiguous required value MUST fail closed.

### 5.1 Git and record authority

1. `S`, `R`, and `H` MUST be exact full lowercase hexadecimal Git commit
   identities of the repository's bound object format. For the repository's
   current SHA-1 object format they are 40 hexadecimal characters;
   abbreviations are prohibited.
2. One successful fresh fetch MUST resolve `H` from the bound repository
   authority and full approved branch ref; cached objects alone are
   insufficient.
3. The current record MUST be the exact blob at the one canonical path in
   `H`; official resolution MUST ignore readiness-like files elsewhere.
4. `R` MUST be derived uniquely under Section 3.3, and
   `S ancestor-of R ancestor-of H` MUST hold in the required first-parent
   authority history.
5. Every governed scope MUST exist at `S` and equal its recorded Git object.
6. No governed object MAY change between `S` and `H`, except the canonical
   readiness-record path itself. Changes outside governed scopes are allowed.
7. The launch-authority snapshot MUST reconstruct exactly under Section 3.6.
8. Preparation MAY require synchronized local and remote heads. Official
   launch MUST ignore local branch position and working-tree contents.

### 5.2 Coherent governed source

At `S`, the protocol, implementation, adapter registration, protocol binding,
Research Execution Specification, profile, experiment configuration,
decision-selection configuration, artifact declarations, readiness control
plane, runtime/dependency manifest, mandatory readiness-test policy, and tests
MUST all exist, be mutually consistent, and match their recorded byte, Git
object, digest, and identity bindings. Exactly one adapter MUST be registered
for the experiment identifier. Missing or duplicate registration MUST fail.

### 5.3 Isolated reconstruction and validation

1. Preparation and launch MUST use clean detached state at `S` under the
   hermetic runtime contract in Section 8.
2. Import and compile validation MUST pass.
3. The repository-mandatory readiness-test set plus adapter additions MUST
   pass from `S` under the recorded environment.
4. Configuration, input, Replay, population, and artifact reconstruction MUST
   be deterministic and repeat to identical identity material.
5. The launch smoke subset, when required by the bound mandatory policy, MUST
   pass immediately before allocation.

### 5.4 External inputs and Replay

Every input MUST satisfy Section 9 and be available as the exact bound bytes.
The outcome-blind Replay, canonical candidate order, decision-selection
material, and first-order Replay identity material MUST reconstruct exactly.
Every Replay unit MUST have one pre-outcome population disposition, and counts
and identities MUST reconcile. A copied unexplained Replay literal is
insufficient.

### 5.5 Profile, isolation, allocation, and output

1. The profile identity and permitted capabilities MUST match the record.
2. Outcome-aware execution MUST satisfy the structural boundary in Section 14.
3. Characterization MUST have no outcome capability or authorization path.
4. The shared allocation authority and writable control storage MUST be
   available and conformant before allocation.
5. Required artifact kinds and a collision-free immutable output policy MUST
   be declared.

### 5.6 Record and seal

The record MUST satisfy Section 6, reproduce its identity, have canonical
bytes, and equal the blob at the canonical path in `H`. `R` MUST be the unique
qualifying seal for that current blob and MUST be reachable on the freshly
fetched approved ref. The current-readiness disposition under Section 10 MUST
be exactly `EXECUTION_READY`.

## 6. Canonical readiness record and identity

### 6.1 Canonical path and experiment identifier

V1 defines exactly one authoritative path:

```text
docs/research/readiness/<experiment-identifier>.json
```

`experiment-identifier` MUST be the lowercase NFC string matching
`[a-z][a-z0-9]*(?:[-_][a-z0-9]+)*`. It MUST contain neither a path separator
nor a dot. Case-folding, aliasing, percent encoding, and alternate
normalizations MUST NOT be accepted. The exact normalized canonical path MUST
participate in readiness identity. Official resolution MUST inspect only that
path. A readiness-like object elsewhere has no official authority.

### 6.2 Required schema

The v1 record MUST contain exactly one `readiness_identity` plus these required
identity-material sections:

| Section | Required material |
| --- | --- |
| `schema` | schema-registry identifier and an ordered declaration for every readiness-v1 record/control-object schema containing object kind, schema identifier, normative artifact path, byte count, SHA-256, Git blob identity, plus the canonical-encoding revision |
| `experiment` | normalized identifier, canonical record path, configuration identity |
| `git_authority` | repository authority identifier, full branch ref, `S` |
| `readiness_specification` | this specification's path, revision, byte/Git-object identities, SHA-256 |
| `control_plane` | validator, orchestrator, serializer, registry, adapter, allocator client/contract, outcome gate, and component identities |
| `source_scopes` | governed path, role, nesting declaration, Git object identity |
| `protocol` | normalized path, identifier, revision, byte count, SHA-256, Git blob |
| `implementation` | unique adapter identifier, entry point, implementation and protocol-binding identities |
| `execution_specification` | path, revision, byte count, SHA-256, identity |
| `execution_profile` | profile name and identity |
| `runtime` | Python/runtime identity, dependency manifest, normalized environment contract |
| `configuration` | experiment and decision-selection identities |
| `external_inputs` | governed input declarations and parser/schema contracts |
| `replay` | construction material, identity, ordering, and population accounting |
| `artifacts` | required artifact declarations and dependency roles |
| `outcome_policy` | permitted/prohibited capabilities and authorization contract |
| `validation` | mandatory test-policy identity, selectors, pass results, compiler/import and reconstruction results |
| `attempt_policy` | allocation contract, attempt identity domain, output and collision policy |

The record MUST contain no unknown or optional fields. The stored
`readiness_identity` MUST be excluded from its own identity material. `R`, `H`,
timestamps, host/operator data, credentials, notes, scientific outcomes,
results, and interpretations MUST NOT occur in identity material. V1 records
MUST NOT contain non-identity metadata.

Every canonical readiness-v1 record or control-object type MUST have exactly
one normative machine-readable field/type schema governed at `S`. Its schema
MUST enumerate every field at every nesting level, its scalar or collection
type, required status, enum domain where applicable, array ordering semantics,
uniqueness key where applicable, and whether additional properties are
permitted. Every field is required at its defined nesting level and additional
properties MUST be prohibited. The schema identifier, path, exact bytes,
SHA-256, and Git blob identity MUST be bound by the readiness record and the
governed control plane. Code-only or undocumented schema interpretation is
insufficient. Independent conforming implementations using the bound schema
MUST agree on acceptance, rejection, and identity material.

### 6.3 Canonical JSON

The record MUST be UTF-8 JSON using only objects, arrays, NFC strings,
integers, and booleans. JSON `null` and floating-point or exponent numbers are
prohibited everywhere in every canonical readiness-v1 record and control
object. V1 defines no nullable field. A future schema revision MAY introduce a
field with explicit normative nullable semantics, but that revision is not v1.
Integers MUST serialize as base-10 with no leading zero, plus sign, decimal
point, exponent, or negative zero.

A field that is not applicable MUST use its schema-defined non-null
representation, such as an empty canonical collection where semantically
valid, an explicit enum or disposition, or a profile-specific schema branch.
It MUST NOT be omitted or represented as `null`. Missing required fields and
unknown fields MUST fail validation.

Object keys MUST be NFC, sorted by Unicode code-point order after
normalization, and unique after normalization. JSON MUST use separators `,`
and `:` with no whitespace. A quote and reverse solidus MUST serialize as
`\"` and `\\`; backspace, tab, LF, form feed, and carriage return MUST use
`\b`, `\t`, `\n`, `\f`, and `\r`; every other U+0000 through U+001F code
point MUST use lowercase `\u00xx`; solidus MUST NOT be escaped; and every
other Unicode scalar MUST be emitted directly as UTF-8. Lone surrogates are
prohibited. The document MUST end in exactly one LF byte. Duplicate keys, a
BOM, invalid UTF-8, unknown fields, missing fields, or alternate valid JSON
spellings MUST fail.

Repository paths MUST be NFC relative POSIX paths. They MUST reject absolute
paths, backslashes, NUL, empty segments, `.` segments, `..` segments, and any
noncanonical alternative. Set-like collections MUST be sorted and unique by:

- source scopes: normalized path, then role;
- control-plane components: stable component identifier;
- external inputs: role, then normalized member path;
- artifact declarations: stable artifact identifier;
- tests: stable test selector; and
- environment declarations: variable name.

Ordered collections, including external collection members, Replay candidate
order, decision-selection order, and dependency order when declared ordered,
MUST preserve declared order and that order participates in identity.
Duplicate stable identifiers MUST fail.

### 6.4 Identity algorithm

Let `M` be the complete record object with `readiness_identity` removed and
canonically serialized as Section 6.3, including its trailing LF. The identity
is the lowercase hex encoding of:

```text
SHA256(
  UTF8("orev3:experiment-execution-readiness:v1\n")
  || M
)
```

This framing is fixed. A conforming implementation MUST NOT insert a length,
NUL, alternate newline, or other separator. Two conforming implementations
MUST produce the same identity for the same valid record. The complete stored
record, including the derived identity, MUST then be serialized under the same
rules.

### 6.5 Other readiness-v1 control identities

Every readiness-v1 control object MUST use Section 6.3 and the same framing as
Section 6.4, substituting exactly one of these domain lines:

| Object | Domain line |
| --- | --- |
| launch-authority snapshot | `orev3:experiment-launch-authority-snapshot:v1\n` |
| immutable input snapshot | `orev3:experiment-input-snapshot:v1\n` |
| allocation receipt | `orev3:experiment-attempt-allocation:v1\n` |
| attempt identity | `orev3:experiment-attempt:v1\n` |
| start or terminal control record | `orev3:experiment-attempt-control:v1\n` |
| outcome authorization | `orev3:experiment-outcome-authorization:v1\n` |
| execution-control manifest | `orev3:experiment-execution-control-manifest:v1\n` |

The object's stored identity field MUST be excluded from its own identity
material. Cross-object references MUST use already-derived identities; cycles
are prohibited. An allocation receipt MAY contain the attempt identity, but
attempt identity material MUST NOT contain the allocation-receipt identity.
Attempt identity instead binds the allocation authority, ordinal, namespace,
and launch authority directly as Section 11.3 requires.

This section applies to readiness records, launch-authority snapshots,
immutable input snapshots, allocation and failure receipts, start and terminal
control records, outcome authorizations, execution-control manifests, and any
other canonical readiness-v1 control object. Each MUST validate against its
exact bound normative schema before its identity can be accepted.

## 7. Git authority and launch snapshot

### 7.1 Fresh authority resolution

The approved repository authority identifier and full ref MUST be
repository-governed. A local alias such as `origin` is only transport
configuration and MUST resolve to an allowlisted canonical endpoint. Each
preparation, status, and launch resolution MUST successfully fetch the exact
approved ref. Failure is `READINESS_UNRESOLVED_REMOTE`; cached-object fallback
is prohibited.

A shallow repository MUST fetch enough first-parent and object history to
prove record introduction, ancestry, and governed diffs. If it cannot, the
operation MUST fail unresolved. Missing cached objects MUST NOT be interpreted
as absence on the authority. A force-push or rewrite is accepted only as the
new fetched `H`; inability to re-establish `S`, `R`, and history produces the
Section 10 disposition.

### 7.2 Preparation and source selection

Normal preparation MUST derive `S` from the exact synchronized local and
fetched remote head; it MUST reject divergence and MUST NOT ask a human to
copy a SHA. It MUST NOT search for the first historically passing commit.
Official launch does not use the local branch and derives authority only from
the fresh remote snapshot.

### 7.3 TOCTOU rule

Launch MUST pin the Section 3.6 snapshot and run all critical checks against
it. A second successful fetch immediately before allocation MUST resolve the
same `H`; otherwise the unresolved launch MUST restart without consuming an
ordinal. Once the allocation receipt is durable, later remote movement MUST
NOT affect the running attempt; it affects future launches only.

### 7.4 Working-tree policy

Preparation MUST reject tracked or untracked content inside governed scopes.
Dirty or untracked content outside them MAY exist, MUST be reported, and MUST
NOT enter the detached checkout or identity. Official launch ignores all local
working-tree content. Whole-tree cleanliness is not required.

## 8. Hermetic source and runtime contract

Preparation and execution MUST occur from an isolated detached checkout of
`S`. The runtime binding MUST identify the Python implementation and exact
version, dependency lockfile or equivalent immutable dependency manifest,
test runner, and platform constraints needed for deterministic behavior.

The checkout root MUST be the working directory. The environment MUST be
sanitized and bind `PYTHONPATH`, module search path, locale, timezone,
`PYTHONHASHSEED` or equivalent hash determinism, and an allowlist of variables
permitted to affect scientific execution. Project modules MUST resolve below
the detached checkout or another explicitly identity-bound immutable
dependency root. Ambient editable installs, the developer working tree, user
site packages, implicit current-directory additions outside `S`, and
unbound executable or module search paths are prohibited.

Infrastructure credentials and secrets MUST be excluded from scientific
identity, scoped only to the orchestrator phase that requires them, and MUST
NOT select data, alter configuration, ordering, randomness, or scientific
semantics. If a credential value can affect scientific semantics, its
semantically relevant contract MUST be identity-bound without exposing the
secret; otherwise official execution MUST be unavailable.

## 9. External inputs and immutable snapshots

### 9.1 V1 input forms

An external governed input MUST be either one regular file or an explicit
manifest containing an identity-bearing ordered collection of regular files.
Symlinks, devices, sockets, undeclared directory traversal, implicit globbing,
and mutable directory enumeration are prohibited. Member paths MUST satisfy
Section 6.3, be unique, and retain manifest order.

Each input declaration MUST bind role, version, exact byte count and SHA-256,
input identity, schema identity, and record/order facts required by the bound
Research Execution Specification. A compressed or container input MUST bind
the exact container bytes, decoder/parser identity and configuration, and
logical schema. Exact byte identity governs eligibility unless the protocol
defines a different explicit external-source contract.

### 9.2 Launch snapshotting

For an external input originating from a mutable locator, launch MUST perform
this order:

1. resolve the declared external-input source;
2. create a complete immutable attempt-local snapshot;
3. hash and validate that final immutable snapshot itself against the sealed
   readiness binding; and
4. only after every required snapshot passes final validation, permit durable
   official attempt allocation.

Final snapshot validation MUST cover exact byte size and SHA-256, ordered
collection membership and identity where applicable, schema, decoder/parser
identity and configuration where applicable, and external-input identity. The
immutable snapshot MUST be complete before scientific input validation can
succeed. Only the validated immutable snapshot identity MAY participate in the
launch-authority and attempt control chain.

The exact validated snapshots MUST be used by ranking, outcome authorization,
evaluation, deterministic reconstruction, and final validation. Mutation,
replacement, deletion, or retargeting of the original mutable locator after
snapshot creation MUST have no effect on the attempt. If the source changes
during snapshot creation so that a coherent immutable snapshot cannot be
established and independently validated, launch MUST fail closed before
allocation. A path that validates mutable bytes and later copies potentially
different bytes is nonconformant.

An immutable content-addressed object MAY serve directly as the immutable
attempt snapshot only after its digest is independently verified against the
sealed binding during launch. A digest or metadata cache associated with a
mutable locator MUST NOT substitute for validation of the final immutable
snapshot.

An absent input is `READINESS_BLOCKED_INPUT_UNAVAILABLE`. Different bytes,
size, schema, ordering, or identity are `READINESS_INPUT_MISMATCH`. An
unavailable exact input MAY later restore eligibility; changed bytes require a
new governed binding and seal.

### 9.3 Outcome-bearing inputs

Readiness MAY hash raw outcome-bearing bytes through a verifier that returns
only digest, size, availability, and snapshot identity. It MUST NOT expose
semantic outcome records to readiness tests, adapters, or ranking code.

Generated artifacts and failure receipts MAY remain ignored runtime objects.
They MUST retain content identities and MUST NOT substitute for source at `S`.

## 10. Derived current-readiness dispositions

Current readiness is derived, never stored. A resolver MUST report exactly one
primary disposition using this precedence:

1. `READINESS_UNRESOLVED_REMOTE`: a fresh authoritative ref cannot be fetched
   or required history/objects cannot be obtained. No lower condition can be
   known authoritatively.
2. `READINESS_AMBIGUOUS`: more than one authoritative interpretation, record,
   qualifying `R`, adapter, or input resolver result remains.
3. `READINESS_INVALID_RECORD`: the canonical blob is absent, malformed,
   noncanonical, identity-inconsistent, binding-inconsistent, or unsupported.
4. `READINESS_ORPHANED`: the record exists but `S`, `R`, required objects, or
   `S ancestor-of R ancestor-of H` cannot be established.
5. `SUPERSEDED`: an explicitly queried historical seal is not the seal of the
   current canonical blob. This disposition is for status/reproduction
   queries; normal launch resolves the current blob directly.
6. `READINESS_STALE`: a governed object changed after `S`, including protocol,
   implementation, specification, profile, readiness control plane, runtime,
   policy, or tests.
7. `READINESS_INPUT_MISMATCH`: located governed input differs from its binding.
8. `READINESS_BLOCKED_INPUT_UNAVAILABLE`: the exact input is temporarily
   unavailable.
9. `EXECUTION_READY`: all invariants hold.

This order gives unresolvable authority and integrity faults priority over
recoverable availability faults. Implementations MUST retain all observed
secondary diagnostics but MUST report the same primary disposition.

Remote advancement only outside governed scopes leaves readiness ready.
Advancement within governed scopes makes it stale. A newer canonical seal
supersedes an older seal. Local ahead/behind state has no launch-authority
effect. Reappearance of byte-identical input MAY clear blocked status;
different bytes remain a mismatch. An unpushed local seal has no current
official authority.

## 11. Official execution contract

### 11.1 Interface and authority

Official execution MUST accept an experiment identifier and resolve the
canonical record from fresh remote authority. It MUST NOT accept a source
commit authority argument. If a development or legacy command exposes such an
option, that option MUST be syntactically unavailable or rejected in official
mode. An instruction to run officially using a named SHA cannot make that SHA
authoritative.

### 11.2 Critical launch sequence

The orchestrator MUST:

1. resolve and validate one launch-authority snapshot;
2. construct the detached hermetic checkout at `S`;
3. create or resolve every immutable external-input snapshot and validate the
   final snapshot bytes and identities under Section 9.2, then validate all
   other bindings, Replay, structural outcome policy, control storage, and
   output policy;
4. run the policy-bound launch smoke subset;
5. perform the required second fetch and restart if `H` changed;
6. atomically persist one allocation receipt; then
7. persist a `STARTED` record immediately before handing control to
   profile-specific experiment execution.

Any failure before step 6 is a readiness or launch rejection and MUST NOT
consume an ordinal. A failed check MUST NOT be repaired or bypassed in place.

### 11.3 Allocation receipt and attempt identity

The immutable allocation receipt MUST bind experiment identifier,
launch-authority snapshot identity, readiness identity, `S`, `R`, `H`, attempt
kind, the ordered validated immutable external-input snapshot identities,
permanent kind-specific ordinal, attempt identity, output namespace identity,
and allocator-contract identity. Attempt identity MUST be a domain-separated
canonical SHA-256 over those same authority fields plus its schema and
output-policy revision. An unvalidated mutable locator or mutable-source digest
MUST NOT replace an immutable snapshot identity in that material.

The allocator MUST atomically compare-and-create the ordinal, receipt,
identity, and namespace across every executor under the same authority. Once
the receipt persists, the ordinal is consumed forever. It MUST NOT be reused
after crash, failure, empty or partial output, or manual artifact deletion. A
retry MUST allocate a new ordinal and identity.

Any pre-existing target path, including an empty directory or symlink, is a
collision. A collision before allocation rejects launch; an inconsistency
discovered after allocation consumes the ordinal and produces `FAILED` or
`INCOMPLETE` as supported by control evidence.

## 12. Attempt durability, recovery, and status

`ALLOCATED` becomes durable when the shared allocator confirms the immutable
receipt. `STARTED` becomes durable when a write-once start record binding that
receipt is durably confirmed immediately before the orchestrator hands control
to profile-specific execution. `STARTED` is a durable commitment to attempt
invocation; it MUST NOT claim or prove that experiment code actually ran. A
crash after `STARTED` but before invocation is valid control history and leaves
the attempt `INCOMPLETE` until recovery evidence permits `FAILED`. Actual
invocation evidence MAY be retained as diagnostic runtime evidence, but v1
does not require another lifecycle state. The terminal control record MUST be
write-once and unique.

A crash after allocation but before `STARTED`, after `STARTED`, during ranking,
after ranking freeze, after outcome authorization, during evaluation, or before
terminal recording leaves the attempt `INCOMPLETE` unless and until recovery
appends an evidence-backed `FAILED` record. Process death, storage failure,
exceptions, ambiguity, or inability to determine scientific validity MUST NOT
become `EXECUTION_INVALID`.

`EXECUTION_VALID` and terminal `VALID` require the scientific Experiment Audit
Manifest mandated by the bound Research Execution Specification to be present,
canonically reconstructable, sealed, and successfully validated for
conformance. The manifest MUST be consistent with the readiness identity,
launch authority, attempt, source, profile, external snapshots, and scientific
bindings owned by its governing specification. Its exact identity and digest
MUST be bound by both the terminal control record and final readiness-v1
execution-control manifest. A terminal control record alone cannot establish
scientific validity. An absent, malformed, noncanonical, unreconstructable,
nonconformant, or authority-inconsistent required scientific manifest MUST NOT
produce `VALID`; the attempt remains `INCOMPLETE` or becomes `FAILED` according
to available control evidence.

`EXECUTION_INVALID` and terminal `INVALID` require explicit immutable governing
evidence that identifies the exact protocol, Research Execution Specification,
or conformance rule establishing scientific invalidity. The terminal control
record and final control manifest MUST bind that evidence's identity and
digest. If the governing Research Execution Specification requires an audit or
conformance manifest for invalid executions, that manifest MUST be present,
canonically reconstructed, validated, and bound as well. Infrastructure
termination, missing evidence, ambiguity, process death, storage failure, or
inability to establish validity MUST NOT become scientific `INVALID`; the
attempt is `INCOMPLETE` or `FAILED` according to the evidence.

Infrastructure termination is `EXECUTION_FAILED`. Recovery MUST NOT resume,
copy, merge, or reinterpret scientific artifacts into another attempt. V1
defines no cross-attempt import or continuation. A retry is always a new
attempt.

## 13. Readiness and launch failure receipts

Readiness and launch failures MUST return a normalized canonical receipt even
if durable storage is unavailable. Failure to persist a required runtime
receipt MUST NOT permit execution. Launch MUST prove writable control storage
before allocation.

The v1 receipt MUST bind schema, failure kind, experiment identifier, candidate
`S` if known, readiness and launch-snapshot identities if known, repository
authority and branch ref, normalized failed invariant/code, completed-check
statuses, `scientific_execution_started=false`, and
`scientific_outcome_evidence=absent`. Its identity is:

```text
SHA256(UTF8("orev3:experiment-readiness-failure-receipt:v1\n") || canonical(receipt_material))
```

Receipt material uses Section 6.3. Receipts MUST be outcome-free,
non-scientific, and ignored runtime artifacts by default. Repository retention
policy SHOULD retain them for audit, but retention or loss does not grant
scientific authority. A receipt MUST distinguish `READINESS_REJECTED`, a
derived current-readiness disposition, and `LAUNCH_REJECTED`.

## 14. Structural outcome-access contract

### 14.1 Common boundary

The official orchestrator MUST be the sole holder or resolver of raw
outcome-source locators and opener authority before authorization. The ranking
environment MUST be a separate process or an equivalently enforceable
capability boundary. It MUST receive only an immutable outcome-blind projection
or a reader structurally incapable of returning outcomes. It MUST NOT receive
a raw outcome path, outcome-bearing parsed record, parser, label provider,
join callback, or outcome opener. Parsing outcome-bearing records and then
projecting fields is not sufficient. Outcome-bearing objects MUST NOT be
instantiated or retained in the ranking environment.

### 14.2 `outcome_aware_v1`

The enforced sequence is:

```text
readiness -> outcome-blind Replay -> ranking -> ranking persistence/freeze
-> ranking reconstruction validation -> attempt-local outcome authorization
-> evaluation process opens outcomes -> join/evaluation
```

Authorization MUST be non-replayable and bind readiness identity, `S`, `R` or
launch-snapshot identity, attempt identity, profile identity, dataset identity,
ordered validated immutable external-input snapshot identities, Replay
identity, outcome-blind provenance identity, ranking-contract identity, exact
frozen ranking-artifact identity, and declared outcome-source identity.
Before opening outcomes, the evaluation environment MUST reconstruct and
validate the unchanged ranking bytes against the authorization. An
authorization from another attempt or ranking is unusable. After authorization
or outcome opening, crash recovery follows Section 12 and cannot resume the
attempt.

### 14.3 `outcome_blind_characterization_v1`

Characterization MUST receive no outcome locator, opener, authorization
factory, parser, label provider, join function, or evaluation callback. It has
no authorization route, and its terminal outcome disposition remains
`prohibited_and_not_performed`.

Historical Experiment 3 and Experiment 4 combined-record loading patterns do
not satisfy this prospective structural isolation requirement. This fact MUST
NOT retroactively invalidate or rewrite those historically governed valid
experiments. Prospective adapters governed by readiness v1 MUST use this
section's boundary.

## 15. Adapter, test, and direct-runner policy

### 15.1 Adapter registry

Exactly one adapter MUST be registered per normalized experiment identifier.
Registry duplicates or absence fail readiness. Registry and adapter identities
are bound at `S`. The adapter's protocol, profile, execution specification,
configuration, external-input binding, source scopes, readiness tests, and
artifact declarations MUST equal the canonical record and MUST NOT be
overridden at launch.

Only the official orchestrator MAY create official allocation receipts,
readiness-bound outcome authorization, or readiness-v1 execution-control
manifests. Prospective direct runners MAY create clearly marked development
artifacts, but cannot mint an official attempt identity or ordinal, official
authorization, official control manifest, or official `EXECUTION_VALID` or
`EXECUTION_INVALID` disposition.

### 15.2 Mandatory readiness-test policy

The repository MUST own a versioned mandatory readiness-test policy. It MUST
bind its identity, exact selectors and commands, test source objects, test
runner, runtime/dependency contract, normalized environment, and fixed launch
smoke subset. An adapter MAY add tests but MUST NOT remove or replace mandatory
tests. All tests run from `S` under Section 8.

Network-dependent readiness tests are prohibited unless every remote object
and transport result is immutable and identity-bound under an explicit input
contract. Test outputs do not enter readiness identity except their normalized
declared pass/fail results and policy-bound result identity. A seal attests only
that the exact governed test set passed in the recorded environment; it does
not attest that implementation is correct. The launch smoke subset MUST rerun;
failure rejects that launch and does not mutate historical seal status.

## 16. Attempt output and execution-control manifest

### 16.1 Namespace

Each allocation maps to one write-once namespace encoding or unambiguously
mapping experiment, kind, permanent ordinal, and attempt identity. A form such
as `executions/official-001-<attempt-prefix>/` MAY be used, but directory names
never establish authority. Existing paths are collisions and MUST NOT be
overwritten, merged, reused, or silently suffixed.

### 16.2 Execution-control envelope

Readiness v1 adds a prospective control manifest above, and without changing,
existing Research Execution Specification scientific manifests. Its append-only
control records MUST bind readiness identity, `S`, `R`, `H`, launch-snapshot
identity, attempt identity/kind/ordinal, allocation receipt identity, external
input snapshot identities, profile identity, terminal scientific-evidence
identity/digest, and final control disposition. For `VALID`, terminal
scientific evidence MUST be the present, canonical, successfully validated
Experiment Audit Manifest required by the bound Research Execution
Specification. For `INVALID`, it MUST include the explicit immutable governing
invalidity evidence required by Section 12 and any audit/conformance manifest
required by the bound specification.

A prospective execution cannot claim `official`, readiness-v1 conformance,
`EXECUTION_VALID`, or `EXECUTION_INVALID` without the required allocation,
control-chain, and control-manifest artifacts. The final scientific audit
manifest remains authoritative for the scientific execution facts it owns;
the readiness control envelope owns launch and attempt authority.

A missing, malformed, noncanonical, unreconstructable, nonconformant, or
authority-inconsistent required Experiment Audit Manifest prohibits `VALID`.
Missing or ambiguous governing invalidity evidence prohibits `INVALID`. In
either case the control disposition MUST remain `INCOMPLETE` or become
`FAILED`, as Section 12 permits.

## 17. Reproduction and historical compatibility

For a prospectively readiness-v1-governed experiment, `reproduction` MUST bind
an existing sealed readiness identity and its historical `S` and inputs.
Source-only reproduction is prohibited. It uses separate allocation kind and
namespace and can never be relabeled official.

`legacy_reproduction` MAY bind historical source identities for experiments
predating readiness v1 under their historical specifications. It MUST NOT
create official readiness-v1 receipts, ordinal, attempt kind, authorization,
control authority, or disposition and cannot later be relabeled official.
Existing direct runners for Experiments 1 through 4 MAY remain for that mode.

Experiments 1 through 4 remain historical. A retrospective readiness record
MUST NOT imply this lifecycle existed for them. This contract applies prospectively
after implementation and adoption. Experiment 5 or any next experiment MUST
NOT execute officially before then.

## 18. Human and Codex operating contract

The safe path is:

```text
review protocol -> implement/test -> commit/push coherent S
-> prepare readiness -> review record -> commit/push R
-> execute sealed ready experiment -> determine validity -> freeze finding
```

Humans and Codex MUST NOT carry a source SHA through normal official execution.
Tooling MUST derive `S`, resolve the current record and `R`, and expose one
current-readiness report. It MUST NOT automatically commit, push, repair, or
approve. Choosing an output directory or calling a direct runner cannot create
official authority.

## 19. Trust boundary and non-goals

`EXECUTION_READY` guarantees coherent remote-backed source and record
authority, clean/hermetic reconstruction, bound inputs and Replay, passed exact
readiness checks, current staleness evaluation, structural profile/outcome
policy, and unambiguous allocation capability. It does not guarantee hypothesis
quality, statistical power, dataset truth beyond its contract, absence of
uncovered bugs, scientific interpretation, predictive value, profitability,
Strategy suitability, production safety, live deployment, transaction
authorization, or authority to risk real SOL.

Readiness is research-integrity infrastructure that improves evidence used in
later capital decisions; it is not a capital-risk control. V1 explicitly does
not require a general workflow engine, database technology, blockchain
anchoring, mandatory signing/KMS, automatic commits or pushes, whole-tree
cleanliness, hypothesis approval, automatic interpretation, artifact upload,
live-mining approval, or retrospective rewriting of Experiments 1 through 4.

## 20. Normative regression requirements

Conformance MUST test these fail-closed cases without official outcomes:

| Case | Required disposition/behavior |
| --- | --- |
| Experiment 2D `3ba070ba3c2173d63df690054c4c91957b640db9` lacks protocol | `READINESS_REJECTED`; no record, allocation, or outcome access |
| Experiment 3 `d06734d715ff85aa6e35d373b6bc6d8854425615` lacks protocol | Same |
| Experiment 4 `ca1e3f722a246b70d61f1b6705a8bbc2806ad416` lacks protocol | Same |
| Manual stale Experiment 4 source request after `c42e2ef2727bcf86c1cad87d42b065b44c0e5ffd` | Official CLI cannot accept source authority |
| Governed source/control-plane drift after seal | `READINESS_STALE` |
| Protocol digest mismatch during preparation / sealed resolution | `READINESS_REJECTED` / `READINESS_INVALID_RECORD` |
| Dataset absent | `READINESS_BLOCKED_INPUT_UNAVAILABLE` |
| Dataset bytes or identity changed | `READINESS_INPUT_MISMATCH` |
| Mutable source changes from bytes A to bytes B while its immutable snapshot is being created | Final immutable snapshot MUST be independently validated: execute only if its coherent final bytes match the sealed binding; otherwise reject before allocation. Validation of A followed by execution of B is prohibited |
| Dirty governed source during preparation | `READINESS_REJECTED` |
| Dirty unrelated documentation | Allowed and reported; never imported |
| Missing/unknown profile | Rejected before seal or launch |
| Premature outcome access | Capability structurally absent; violation yields `FAILED`, never silent outcome access |
| Characterization requests outcome | Structurally unavailable and rejected |
| Readiness-record tampering/noncanonical bytes | `READINESS_INVALID_RECORD` |
| Unpushed readiness seal | Not official authority; not `EXECUTION_READY` |
| Fresh remote cannot resolve or history is shallow/incomplete | `READINESS_UNRESOLVED_REMOTE` |
| Local/remote divergence | Preparation rejects; launch ignores local state |
| Required readiness test or launch smoke test fails | Preparation rejection / launch rejection |
| Clean checkout cannot import/compile | `READINESS_REJECTED` |
| Replay reconstruction mismatch | Rejected before allocation |
| Pre-existing output, including empty directory or symlink | Collision; no overwrite |
| Ambiguous record, adapter, resolver, or `R` | `READINESS_AMBIGUOUS` |
| Simultaneous launches | Unique permanent ordinals and receipts |
| Crash after allocation at every Section 12 boundary | Ordinal consumed; `INCOMPLETE` then evidence-backed `FAILED` only |
| Allocation and `STARTED` exist, terminal control attempts `VALID`, but the required scientific Experiment Audit Manifest is absent | `VALID` is prohibited; disposition remains `INCOMPLETE` or becomes `FAILED` according to available evidence |
| Direct prospective runner | Cannot create official authority or disposition |
| Remote changes between two pre-allocation fetches | Resolution restarts; no ordinal consumed |
| Remote changes after allocation | Running attempt remains bound to prior snapshot; future launch reevaluates |
| Authorization replay across attempts/rankings | Rejected before outcome opening |

Historical commit fixtures MAY be represented by temporary repositories that
reproduce the relevant trees, while also verifying cited commits when locally
available.

## 21. Conformance

An implementation MAY claim `experiment-execution-readiness-v1` conformance
only if it demonstrates:

1. interoperable null-free normative schemas and canonical record, readiness,
   launch-snapshot, receipt, attempt, input-snapshot, authorization, and
   control-manifest reconstruction;
2. unique canonical record/R authority from fresh remote state;
3. exact `S ancestor-of R ancestor-of H` and stale/supersession behavior;
4. detached hermetic preparation and execution without working-tree imports;
5. governed readiness control plane, adapter registry, runtime, dependency,
   test-policy, and smoke-test binding;
6. atomic shared allocation, permanent ordinals, collision rejection, the
   durable-commitment meaning of `STARTED`, durable control transitions, and
   deterministic crash recovery;
7. creation of immutable attempt-local snapshots before final validation,
   exact validation of those final snapshot bytes before allocation, and use
   of the same snapshots throughout execution;
8. official CLI rejection of manual source authority and direct-runner
   inability to mint official artifacts;
9. structural outcome isolation, attempt-local non-replayable authorization,
   ranking reconstruction, and characterization with no outcome route;
10. mutually exclusive current-readiness dispositions with Section 10
    precedence;
11. non-scientific canonical failure receipts and prospective execution-control
    envelopes layered above unchanged scientific audit manifests, with
    validated scientific manifests required for `VALID` and explicit immutable
    governing evidence required for `INVALID`;
12. all Section 20 regressions; and
13. historical/legacy reproduction compatibility without false prospective
    authority.

Conformance establishes readiness control-plane integrity only. The bound
Research Execution Specification and experiment protocol remain authoritative
for scientific execution conformance, validity, and interpretation.
