# Execution Readiness v1.1 Prerequisite Authority Identities Decision

## Decision status

- Decision identifier: `execution-readiness-v1.1-prerequisite-authority-identities`
- Decision type: bounded prerequisite-authority identity and compatibility governance
- Status: Proposed for targeted adversarial review
- Governing branch: `research/post-v1`
- Governing continuation commit: `236dbee9e2909cb743d038efb2e7186fe574ba90`
- Current continuation checkpoint: [Phase 3C Intermediate Checkpoint](../../project-checkpoints/ore-v3-execution-readiness-phase3c-intermediate.md)
- Governing specification: [Experiment Execution Readiness v1.1](../specifications/experiment-execution-readiness-v1.1.md)
- Governing specification SHA-256: `e938499cc254ce2d65fce925fb6e33c5d8b9dcea73a91a2c01e1017e8fb17da9`
- Prior clarification governance: [Execution Readiness v1 Clarification Decision](execution-readiness-v1-clarification-decision.md)
- Prior clarification-governance SHA-256: `ce9e7cd57df0d31db5aea0c7674edc3b3b717b96a790d5c7e3075364df151477`
- Readiness-test-policy versioning governance: [Readiness-Test-Policy Versioning Decision](execution-readiness-v1.1-readiness-test-policy-versioning.md)
- Readiness-test-policy versioning SHA-256: `e0d79b517b126633bb2f39448c61a84307dfd3b51628a39c8501eb7653fe20fd`
- Implementation authorized by this document: no
- Execution-readiness lifecycle semantic change: none

This decision closes exactly two missing prerequisite-authority identity
definitions required to finish Phase 3C Slice 2. It does not reopen frozen
v1.1, change lifecycle boundaries, or authorize any operational action.

## 1. Problem and decision scope

The prospective Slice-1 `attempt-authority-contract` schema contains
`control_storage_contract_identity`, and the historically bound
`adapter-declaration` schema contains `attempt_output_declaration_identity`.
Both fields are structurally SHA-256 values, but frozen authority did not
define sufficient canonical material and domain separation for independent
reconstruction.

Accepting either value by syntax alone would permit authority substitution.
Aliasing either value to a nearby but semantically different identity would
conflate authority layers. This decision therefore freezes:

1. a distinct reusable control-storage contract identity;
2. an adapter-specific attempt-output declaration identity;
3. the closed embedded canonical material for both identities;
4. a prospective adapter-declaration v2 compatibility mechanism;
5. the prospective correction of the Slice-1 attempt-authority schema;
6. exact cross-binding and mismatch rules; and
7. one acyclic identity dependency graph.

## 2. Control-storage semantic decision

### 2.1 Exact semantic purpose

`control_storage_contract_identity` identifies one reusable governed
control-storage contract. The contract declares the canonical control-record,
manifest, persistence, and recovery semantics that a committed implementation
must provide.

It is distinct from:

- `allocation_authority_identity`, which identifies one configured shared
  allocation-authority instance and its continuous permanent ledger/control
  history;
- `allocator_contract_identity`, which identifies reusable allocation and
  namespace-allocation semantics;
- `control_storage_component_identity`, which identifies the exact committed
  implementation component bytes and repository binding; and
- the physical backend or transport used by an authority instance.

The contract identity MUST NOT contain or derive from a machine-local storage
root, filesystem path, service endpoint, credential, secret, backend alias,
process identifier, host identifier, timestamp, current availability,
writability result, current contents, or operational health observation.

### 2.2 Committed component binding

The prospective `attempt-authority-contract` contains one closed
`control_storage_component` object with exactly these fields in canonical
object-key order:

1. `component_identifier`;
2. `component_identity`;
3. `git_object_identity`;
4. `path`;
5. `role`;
6. `sha256`.

`role` is exactly `control_storage`. `path` is a normalized safe
repository-relative POSIX path to a regular Git blob at source commit `S`.
`git_object_identity` and `sha256` bind that exact blob. The component identity
uses the existing control-component domain and algorithm:

```text
SHA256(
  UTF8("orev3:readiness-control-component:v1\n")
  || canonical(component material excluding component_identity)
)
```

The role token is prospective embedded attempt-authority material. It does not
mutate or reinterpret the historically bound readiness-record control-plane
schema or historical control-component lists.

### 2.3 Exact control-storage canonical material

`control_storage_contract_identity_material` is a closed object containing
exactly these fields in canonical object-key order:

1. `attempt_control_record_schema_identifier` — exactly
   `attempt-control-record-v1`;
2. `control_storage_component_identity` — exactly the reconstructed identity
   of the sibling `control_storage_component` object;
3. `control_storage_contract_schema_revision` — exactly
   `control-storage-contract-identity-material-v1`;
4. `execution_control_manifest_schema_identifier` — exactly
   `execution-control-manifest-v1`;
5. `persistence_contract_revision` — exactly
   `shared-append-only-control-history-v1`;
6. `recovery_contract_revision` — exactly
   `atomic-no-live-owner-fence-and-append-failed-v1`.

No other field is permitted.

The persistence and recovery revision tokens declare required contract
semantics. Their presence does not prove that a backend is live, writable,
shared, atomic, durable, correctly fenced, or operationally conformant. Those
proofs remain later launch/control-lifecycle responsibilities.

### 2.4 Exact control-storage domain and identity

Let `C` be the Section 2.3 material serialized under the frozen v1 canonical
JSON rules, including its trailing LF. The exact domain-separation line is:

```text
orev3:experiment-control-storage-contract:v1\n
```

The identity is:

```text
control_storage_contract_identity = lowercase_hex(
  SHA256(
    UTF8("orev3:experiment-control-storage-contract:v1\n")
    || C
  )
)
```

The material does not contain `control_storage_contract_identity` and therefore
has no self-cycle.

### 2.5 Relationship to allocation and allocator authority

The control-storage material deliberately does not contain
`allocation_authority_identity` or `allocator_contract_identity`. It is a
reusable contract and MAY be selected by more than one configured authority
instance or allocator contract.

The one committed prospective `attempt-authority-contract` at:

```text
config/research/readiness/attempt-authority-contract-v1.json
```

binds as sibling authoritative fields:

- `allocation_authority_identity` and its exact embedded material;
- `allocator_contract_identity`;
- `control_storage_component`;
- `control_storage_contract_identity_material`; and
- `control_storage_contract_identity`.

That complete committed contract is reconstructed from its exact safe Git blob
at `S`. A different allocation authority, allocator contract, storage
component, storage contract material, contract identity, path, Git object, or
byte digest is a different binding and MUST fail substitution checks.

Changing the reusable control-storage contract for an existing allocation
authority requires a newly governed readiness state. It does not rename,
reset, fork, or erase the existing allocation-authority ledger/history.

### 2.6 Reconstruction and mismatch rules

Prospective validation MUST:

1. reconstruct the contract bytes from the normative path at `S`;
2. validate the selected prospective attempt-authority schema;
3. reconstruct `allocation_authority_identity` independently;
4. reconstruct `allocator_contract_identity` under its already-governed
   implementation/contract binding;
5. reconstruct the sibling `control_storage_component.component_identity`;
6. require the material's `control_storage_component_identity` to equal that
   reconstructed component identity;
7. reconstruct `control_storage_contract_identity` from Section 2.4; and
8. require exact equality with the declared identity.

Missing fields, additional fields, alternate revision tokens, SHA-shaped
substitution, another source commit, another repository authority, another
component, another contract, wrong Git mode/object, wrong path, or mismatched
bytes MUST fail closed.

## 3. Attempt-output declaration semantic decision

### 3.1 Exact semantic purpose

`attempt_output_declaration_identity` identifies one adapter-specific governed
declaration that binds the selected experiment adapter and its canonical
artifact declarations to the exact attempt/output authority required before
candidate construction.

It is not equivalent to `output_policy_identity`. The existing output-policy
identity identifies reusable output/collision semantics. It does not by itself
bind an adapter, experiment, allocation authority, allocator contract,
control-storage contract, output-namespace policy, or complete artifact
declaration set.

### 3.2 Exact attempt-output canonical material

`attempt_output_declaration_identity_material` is a closed object containing
exactly these fields in canonical object-key order:

1. `adapter_identifier` — exactly the containing adapter declaration's stable
   adapter identifier;
2. `allocation_authority_identity` — exactly the independently reconstructed
   selected allocation-authority instance identity;
3. `allocator_contract_identity` — exactly the independently reconstructed
   allocator-contract identity selected by the attempt-authority contract;
4. `artifact_declaration_identities` — the exact declaration identities from
   the containing adapter's artifact declarations, ordered by normalized
   `artifact_identifier`, with no duplicate identifier or identity;
5. `attempt_output_declaration_schema_revision` — exactly
   `attempt-output-declaration-identity-material-v1`;
6. `control_storage_contract_identity` — exactly the independently
   reconstructed selected control-storage contract identity;
7. `experiment_identifier` — exactly the containing adapter declaration's
   normalized experiment identifier;
8. `output_namespace_identity_policy` — exactly
   `output-namespace-identity-material-v1` and exactly equal to the selected
   attempt-authority contract value;
9. `output_policy_identity` — exactly the independently reconstructed existing
   artifact/output-policy identity for the selected profile and artifact
   declaration evidence;
10. `output_policy_revision` — exactly `readiness-v1-output-policy`.

No other field is permitted. The collection MAY be empty only if the selected
governed execution profile and artifact contract independently permit an empty
artifact declaration set; this material does not weaken profile-specific
artifact requirements.

The material MUST NOT contain `adapter_identity`, attempt identity, output
namespace identity, ordinal, allocation receipt identity, realized output
path, candidate/readiness identity, `R`, `H`, timestamps, outcomes, labels,
winners, results, diagnostics, local paths, or backend configuration.

### 3.3 Exact attempt-output domain and identity

Let `O` be the Section 3.2 material serialized under the frozen v1 canonical
JSON rules, including its trailing LF. The exact domain-separation line is:

```text
orev3:experiment-attempt-output-declaration:v1\n
```

The identity is:

```text
attempt_output_declaration_identity = lowercase_hex(
  SHA256(
    UTF8("orev3:experiment-attempt-output-declaration:v1\n")
    || O
  )
)
```

The material excludes both `attempt_output_declaration_identity` and
`adapter_identity`. It therefore has neither a self-cycle nor an adapter cycle.

### 3.4 Exact cross-binding rules

Prospective validation MUST independently reconstruct and require equality for:

- top-level adapter identifier and material adapter identifier;
- top-level experiment identifier and material experiment identifier;
- selected attempt-authority allocation identity and material allocation
  identity;
- selected allocator-contract identity and material allocator identity;
- selected control-storage contract identity and material control-storage
  identity;
- the exact canonical adapter artifact declaration identity vector and the
  material vector;
- Phase-3B artifact declaration evidence and material output-policy identity;
- the selected attempt-authority output-namespace policy and material value;
- the v1.1 output-policy revision and material revision; and
- the declared attempt-output identity and the reconstructed Section 3.3
  identity.

Duplicate artifact identifiers or identities, alternate ordering, missing or
extra declarations, another adapter, experiment, source commit, repository
authority, attempt authority, allocator contract, control-storage contract,
output policy, namespace policy, profile evidence, or artifact evidence MUST
fail closed. A well-formed SHA value never establishes authority without these
reconstructions.

## 4. Prospective adapter-declaration v2

### 4.1 Historical adapter v1 remains immutable

The historical adapter-declaration authority remains:

| Coordinate | Historical value |
| --- | --- |
| Semantic object kind | `adapter-declaration` |
| Registry identifier | `adapter-declaration-v1` |
| Schema `$id` | `orev3://schemas/execution-readiness/v1/adapter-declaration` |
| Schema path | `src/orev3/execution/schemas/v1/adapter-declaration.schema.json` |
| Schema title | `AdapterDeclarationV1` |
| Schema version | `1` |
| Schema SHA-256 | `55fccfb6984b2a565f2d02abc913f76306f774f4e7445ff31c1cb74ffb418cc4` |

Historical Phase 3A/3B registries, evidence, and reconstruction continue to
select these exact bytes. They MUST NOT be modified, relabeled, or interpreted
as v2.

### 4.2 Exact prospective v2 coordinates

The prospective adapter revision is:

| Coordinate | Governed value |
| --- | --- |
| Semantic object kind | `adapter-declaration` |
| Registry identifier | `adapter-declaration-v2` |
| Schema `$id` | `orev3://schemas/execution-readiness/v1/adapter-declaration-v2` |
| Schema path | `src/orev3/execution/schemas/v1/adapter-declaration-v2.schema.json` |
| Schema title | `AdapterDeclarationV2` |
| Schema version | `2` |

The v2 schema retains every governed v1 field and structural restriction,
requires `schema_version=2`, and adds the required closed
`attempt_output_declaration_identity_material` defined in Section 3.2. The
existing `attempt_output_declaration_identity` field remains required and is
reconstructed under Section 3.3.

The existing adapter identity domain remains:

```text
orev3:readiness-adapter-declaration:v1\n
```

`adapter_identity` is reconstructed over the complete canonical v2 adapter
material excluding only `adapter_identity`. Because the attempt-output
material excludes `adapter_identity`, this derivation is acyclic. The changed
schema version and added material produce a distinct adapter identity without
relabeling v1.

The v2 schema bytes do not yet exist. This decision therefore does not state
or anticipate their content SHA-256 or Git blob identity.

### 4.3 Explicit historical/prospective selection

Selection is exact:

| Selected registry | Adapter member | Count |
| --- | --- | ---: |
| Historical Phase 2 | none | 6 |
| Historical Phase 3A | `adapter-declaration-v1` | 10 |
| Historical Phase 3B | `adapter-declaration-v1` | 20 |
| Prospective v1.1 Phase 2 overlay | none | 6 |
| Prospective v1.1 Phase 3A overlay | `adapter-declaration-v2` | 10 |
| Prospective v1.1 Phase 3B overlay | `adapter-declaration-v2` | 20 |
| Prospective v1.1 final registry | `adapter-declaration-v2` | 29 |

Every selected registry containing adapter declarations has exactly one member
for semantic kind `adapter-declaration`. No selected registry contains both
revisions. Repository coexistence of both schema files does not grant both
authority.

Historical APIs MUST explicitly select historical policies. Prospective v1.1
preparation and Phase 3C MUST explicitly select prospective overlays. Selection
MUST NOT depend on filesystem enumeration, a `latest` alias, caller-supplied
authority, ambient configuration, or fallback between revisions.

## 5. Prospective attempt-authority schema correction

The `attempt-authority-contract` schema was introduced by Phase 3C Slice 1 and
is not a member of the historically bound Phase 2, Phase 3A, or Phase 3B
registries. No historical evidence is governed by its current Slice-1 bytes.

It MUST therefore be corrected prospectively in place under its existing
coordinates:

| Coordinate | Retained value |
| --- | --- |
| Semantic object kind | `attempt-authority-contract` |
| Registry identifier | `attempt-authority-contract-v1` |
| Schema `$id` | `orev3://schemas/execution-readiness/v1/attempt-authority-contract` |
| Schema path | `src/orev3/execution/schemas/v1/attempt-authority-contract.schema.json` |
| Schema title | `AttemptAuthorityContractV1` |
| Schema version | `1` |
| Normative contract path | `config/research/readiness/attempt-authority-contract-v1.json` |

The corrected schema adds and requires the closed
`control_storage_component` and
`control_storage_contract_identity_material` structures while retaining the
declared `control_storage_contract_identity`. The future prospective 29-member
schema policy MUST bind the corrected actual bytes and digest at the future
source commit `S`.

The Slice-1 commit and its reviewed digest remain immutable historical
implementation milestones. Prospective correction does not rewrite that
commit, but no new schema revision or second semantic object kind is required
because no evidence has used the incomplete prospective schema as governing
authority.

## 6. Exact acyclic identity graph

In the graph below, `A -> B` means that `B` canonically depends on or binds
`A`:

```text
repository_authority_identifier
+ allocation_authority_identifier
  -> allocation_authority_identity

committed allocator contract and implementation binding
  -> allocator_contract_identity

committed control_storage_component bytes/Git binding
  -> control_storage_component_identity

control_storage_component_identity
+ control-record/manifest schema identifiers
+ persistence/recovery contract revisions
  -> control_storage_contract_identity

allocation_authority_identity
+ allocator_contract_identity
+ control_storage_contract_identity
  -> committed attempt-authority-contract binding at S

canonical artifact declarations
  -> ordered artifact_declaration_identities
  -> artifact-declaration evidence
  -> output_policy_identity

adapter_identifier
+ experiment_identifier
+ allocation_authority_identity
+ allocator_contract_identity
+ control_storage_contract_identity
+ ordered artifact_declaration_identities
+ output_policy_identity
+ output_policy_revision
+ output_namespace_identity_policy
  -> attempt_output_declaration_identity

complete adapter-v2 material
+ attempt_output_declaration_identity
  -> adapter_identity

allocation_authority_identity
+ allocator_contract_identity
+ experiment_identifier
+ attempt_kind
+ output_policy_revision
+ permanent_ordinal
  -> output_namespace_identity

readiness_identity + S + R + H
+ launch_authority_snapshot_identity
+ ordered immutable input snapshot identities
+ allocation_authority_identity
+ allocator_contract_identity
+ output_namespace_identity
+ experiment_identifier + attempt_kind + permanent_ordinal
  -> attempt_identity
```

The graph is acyclic because:

- allocation-authority material contains neither contract nor namespace
  identities;
- allocator-contract and control-storage identities contain no attempt,
  adapter, namespace, receipt, or readiness identity;
- attempt-output material excludes `adapter_identity`, namespace identity,
  attempt identity, and receipts;
- adapter identity depends on attempt-output identity, never the reverse;
- output namespace depends only on pre-attempt allocation coordinates and does
  not depend on adapter, attempt-output identity, attempt identity, or receipt;
  and
- attempt identity is downstream of namespace identity and never feeds back.

## 7. Historical and prospective preservation

This decision freezes that:

- historical Phase 2, Phase 3A, and Phase 3B schemas, policies, evidence,
  identities, checkpoints, and source authority remain unchanged;
- historical adapter-declaration v1 bytes remain unchanged;
- historical readiness-test-policy v1 bytes and selection remain unchanged;
- the already-governed prospective readiness-test-policy v2 coordinates,
  overlays, identity domain, evidence compatibility, and no-smoke-execution
  rule remain unchanged;
- no historical evidence is recomputed, repaired, relabeled, or interpreted as
  prospective v1.1 evidence;
- fresh prospective evidence binds adapter v2, readiness-test-policy v2, the
  corrected attempt-authority schema, and the future source commit `S`; and
- no production adapter, allocator, control-storage implementation,
  orchestrator, or outcome gate is supplied by this decision.

## 8. Registry decision

The prospective final schema registry remains exactly **29 semantic object
kinds**.

This decision adds no top-level object kind:

- control-storage component and contract material are closed definitions
  inside `attempt-authority-contract`;
- adapter-declaration v2 substitutes for v1 under the existing semantic kind;
  and
- corrected attempt-authority bytes remain under their existing semantic kind.

The historical registry counts remain 6/10/20. Prospective v1.1 overlays remain
6/10/20/29 while applying both already-governed readiness-test-policy-v2
substitution and this decision's adapter-declaration-v2 substitution.

## 9. Independent remaining Slice-2 corrections

The following reviewed findings remain independent implementation corrections
after this governance is frozen:

1. `launch_smoke_selectors` MUST be constrained to the governed mandatory
   readiness selector set while preserving canonical empty, sorted, unique
   behavior and no preparation-time smoke execution.
2. Duplicate singleton source-scope authority roles MUST reject while
   legitimate multi-path, non-singleton governed scopes remain supported.

Neither finding changes either identity material, domain, adapter-versioning
rule, or registry count in this decision.

## 10. Implementation consequences and required regressions

Later bounded Slice-2 correction MUST prove at least:

1. exact control-storage material and identity reconstruction;
2. exact committed component Git/path/byte binding;
3. rejection of allocation-authority, allocator-contract, component,
   control-storage-contract, repository, source, path, Git-object, and raw-SHA
   substitution;
4. exact attempt-output material and identity reconstruction;
5. rejection of adapter, experiment, attempt-authority, allocator,
   control-storage, output-policy, namespace-policy, profile, artifact-vector,
   source, and raw-SHA substitution;
6. adapter identity remains acyclic and changes when any governed
   attempt-output binding changes;
7. historical adapter v1 remains byte-identical and historically selected;
8. prospective Phase 3A/3B/29 overlays select only adapter v2;
9. historical/prospective readiness-test-policy selection remains unchanged;
10. prospective registry counts remain exactly 6/10/20/29;
11. no selected registry contains both revisions of one semantic kind;
12. no backend path, endpoint, credential, live status, outcome, diagnostic,
    or machine-local value enters either identity;
13. no identity cycle exists; and
14. validation invokes no control-storage backend, allocator, smoke selector,
    outcome capability, or experiment code.

Exact future schema and policy digests MUST be computed only after exact bytes
exist. This decision does not invent those digests or Git blobs.

## 11. Non-goals and unchanged boundaries

This decision does not authorize or implement:

- live control-storage access or availability checks;
- backend writability, operational atomicity, fencing, persistence, migration,
  or recovery execution;
- attempt or ordinal allocation;
- allocation receipts or namespace realization;
- readiness-candidate construction or persistence;
- `READINESS_VALIDATED`, `READINESS_REJECTED`, or `EXECUTION_READY` minting;
- seal `R`, current readiness, launch, second fetch, or smoke execution;
- control-record or control-manifest creation;
- ranking, ranking freeze, outcome authorization, or outcome access;
- evaluation or experiment execution;
- Experiment 5, mining, wallet, transaction, live-capital, or real-SOL work;
  or
- correction of the launch-smoke subset or singleton-role implementation
  findings.

Contract declarations are readiness-time authority. Live operational proof
remains owned by later lifecycle stages exactly as frozen v1.1 requires.

## 12. Self-review and normative closure

This decision was checked adversarially for the previously unresolved choices:

- neither identity aliases allocation authority, allocator contract, generic
  component identity, or output-policy identity;
- contract, authority instance, policy, declaration, implementation, and
  backend semantics remain distinct;
- `adapter_identity` is excluded from attempt-output material, eliminating the
  prospective adapter cycle;
- attempt identity and receipts remain strictly downstream;
- adapter, attempt-authority, allocator, control-storage, output-policy, and
  artifact substitution all require reconstructed equality and fail closed;
- historical schemas are not mutated in place;
- prospective revision selection is explicit and has no ambient/latest/fallback
  route;
- no selected registry gains a duplicate semantic kind or a thirtieth member;
- machine-local/backend data and outcomes are excluded from canonical identity;
  and
- exact names, tokens, field sets, field order, domains, schema coordinates,
  paths, selection rules, and cross-bindings are closed above.

No normative choice remains within the two prerequisite-authority identity
gaps resolved by this decision. Future implementation must derive digests and
Git identities mechanically from the reviewed bytes and source commit.
