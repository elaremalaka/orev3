# Execution Readiness v1.1 Readiness-Record v2 Decision

Status: **Proposed for targeted adversarial review**

## 1. Purpose and authority

This decision resolves the remaining repository-compatibility and canonical
representation questions for Execution Readiness Phase 3C Slice 3. It is a
narrow companion to:

- the [Phase 3C intermediate checkpoint](../../project-checkpoints/ore-v3-execution-readiness-phase3c-intermediate.md);
- [Execution Readiness v1.1](../specifications/experiment-execution-readiness-v1.1.md);
- the [v1 clarification decision](execution-readiness-v1-clarification-decision.md);
- the [readiness-test-policy v2 decision](execution-readiness-v1.1-readiness-test-policy-versioning.md); and
- the [prerequisite-authority identity decision](execution-readiness-v1.1-prerequisite-authority-identities.md).

Those tracked authorities remain primary. This decision does not change the
v1.1 lifecycle, introduce a new semantic object kind, or authorize runtime
behavior. It fixes one prospective readiness-record revision, one necessary
prospective profile-conformance-evidence revision, one additive prospective
adapter-declaration revision, their overlay selection, and the exact
readiness-record-v2 field model.

## 2. Historical authority remains immutable

### 2.1 Historical readiness record

The historical readiness-record authority remains:

| Coordinate | Historical value |
| --- | --- |
| Semantic object kind | `readiness-record` |
| Registry identifier | `readiness-record-v1` |
| Schema `$id` | `orev3://schemas/execution-readiness/v1/readiness-record` |
| Schema path | `src/orev3/execution/schemas/v1/readiness-record.schema.json` |
| Schema title | `ReadinessRecordV1` |
| Schema SHA-256 | `c354fa32d8882b8fd8231fa4fed0d943b6cac28dec43fe879d5df525f9d163b7` |

Historical Phase 2, Phase 3A, and Phase 3B registry policies continue to
select those exact bytes. The schema MUST NOT be edited, reinterpreted,
recomputed, or relabeled as prospective v1.1 authority.

### 2.2 Historical profile evidence

The historical `profile-conformance-evidence` v1 schema and evidence remain
immutable. In particular, no historical characterization evidence is
rewritten merely because its historical closed schema carried an
`authorization_contract_identity` field. Historical evidence is interpreted
only under its original schema, policy, source commit, and lifecycle.

This prospective decision does not make that historical field an
authorization route and does not permit it in new characterization evidence.

## 3. Prospective schema revisions

### 3.1 Readiness-record v2 coordinates

The prospective revision is exactly:

| Coordinate | Governed value |
| --- | --- |
| Semantic object kind | `readiness-record` |
| Registry identifier | `readiness-record-v2` |
| Schema `$id` | `orev3://schemas/execution-readiness/v1/readiness-record-v2` |
| Schema path | `src/orev3/execution/schemas/v1/readiness-record-v2.schema.json` |
| Schema title | `ReadinessRecordV2` |
| Schema version | `2` |

The record has no top-level `schema_version` field. Revision authority is the
selected schema declaration in the governed registry, including its registry
identifier, `$id`, path, exact bytes, digest, Git blob, and source commit.

### 3.2 Profile-conformance-evidence v2 coordinates

The prospective profile-evidence revision is exactly:

| Coordinate | Governed value |
| --- | --- |
| Semantic object kind | `profile-conformance-evidence` |
| Registry identifier | `profile-conformance-evidence-v2` |
| Schema `$id` | `orev3://schemas/execution-readiness/v1/profile-conformance-evidence-v2` |
| Schema path | `src/orev3/execution/schemas/v1/profile-conformance-evidence-v2.schema.json` |
| Schema title | `ProfileConformanceEvidenceV2` |
| Schema version | `2` |

Its identity domain remains byte-for-byte:

```text
orev3:experiment-profile-conformance-evidence:v1\n
```

The changed closed material and `schema_version=2` distinguish prospective
evidence without relabeling historical evidence.

### 3.3 Adapter-declaration v3 coordinates

The frozen adapter-declaration-v2 schema is an immutable Slice-2 milestone.
Its SHA-256 remains:

```text
a58a5596ae30355657a994873134e1696e6cb614b51c21555314cd663e9bebd0
```

It MUST NOT be edited to add the complete v1.1 external-input model. That
model is governed by this prospective same-kind revision:

| Coordinate | Governed value |
| --- | --- |
| Semantic object kind | `adapter-declaration` |
| Registry identifier | `adapter-declaration-v3` |
| Schema `$id` | `orev3://schemas/execution-readiness/v1/adapter-declaration-v3` |
| Schema path | `src/orev3/execution/schemas/v1/adapter-declaration-v3.schema.json` |
| Schema title | `AdapterDeclarationV3` |
| Schema version | `3` |

Adapter v3 retains every closed v2 field and every v2 prerequisite-authority,
control-storage, attempt-output, profile-contract, artifact, implementation,
and policy cross-binding. Its only additive authority is the complete
external-input representation in Section 19. It MUST NOT weaken or omit any
Slice-2 binding. Its adapter identity retains domain
`orev3:readiness-adapter-declaration:v1\n`; the complete changed closed material and
`schema_version=3` distinguish v3.

### 3.4 No anticipated byte identities

No new schema's byte count, SHA-256, or Git blob identity is fixed before its
exact reviewed bytes exist. Future prospective policies MUST bind the actual
reviewed values at source commit `S`.

## 4. Historical and prospective registry overlays

Selection is explicit and exact:

| Selected registry | Readiness record | Adapter declaration | Readiness-test policy | Profile evidence | Count |
| --- | --- | --- | --- | --- | ---: |
| Historical Phase 2 | v1 | none | v1 | none | 6 |
| Historical Phase 3A | v1 | v1 | v1 | none | 10 |
| Historical Phase 3B | v1 | v1 | v1 | v1 | 20 |
| Prospective v1.1 Phase 2 | v2 | none | v2 | none | 6 |
| Prospective v1.1 Phase 3A | v2 | v3 | v2 | none | 10 |
| Prospective v1.1 Phase 3B | v2 | v3 | v2 | v2 | 20 |
| Prospective v1.1 final | v2 | v3 | v2 | v2 | 29 |

The corrected `attempt-authority-contract` remains under its governed existing
kind and coordinates. Every selected registry contains exactly one revision
of each semantic kind. Repository coexistence does not confer simultaneous
membership.

Historical reconstruction MUST select historical policies. Prospective v1.1
preparation and Phase 3C MUST select prospective overlays. Selection MUST NOT
depend on filesystem enumeration, a `latest` alias, ambient configuration,
fallback, or a caller-supplied registry or revision.

Adapter selection is therefore exact: historical Phase 3A/3B selects v1;
the already-frozen Slice-2 source authority selects v2; and fresh
post-governance prospective v1.1 Phase 3A/3B/readiness authority selects v3.
No selected registry contains two adapter revisions. Existing v1 or v2
evidence is never relabeled as v3 evidence.

The prospective final registry identifier remains exactly:

```text
readiness-v1-schema-registry-v1
```

That identifier names the stable execution-readiness `v1` schema-family
registry. It does not assert membership of `readiness-record-v1`. A selected
registry is distinguished by its exact ordered member declarations, paths,
bytes, digests, Git blobs, and `S`. No second aggregate registry identity and
no thirtieth semantic kind are introduced.

## 5. Common canonical rules

Readiness-record v2 contains only JSON objects, arrays, NFC strings, integers,
and booleans under the v1.1 canonical JSON rules. Every field defined below is
required at its defined nesting level. Every object is closed. `null`, unknown
fields, omitted fields, floating-point values, and noncanonical collections
are prohibited.

Unless a more specific rule is stated:

- an identity or SHA-256 is a lowercase 64-hex string;
- a Git object identity satisfies the repository's governed object format;
- a byte count is a nonnegative integer;
- a repository path is a safe normalized relative POSIX path;
- a set-like string or identity collection is sorted by Unicode code-point
  order, unique, and may be empty only where its semantics permit emptiness;
- an ordered scientific or declaration collection preserves its expressly
  governed order and MUST NOT be value-sorted; and
- every path, byte count, digest, Git object, identity, and cross-reference is
  reconstructed from authority at the same `S`, not accepted because it has a
  syntactically valid shape.

The only exception to the identity syntax rule in this decision is the exact
`not_applicable` sentinel in an excluded population disposition's
`replay_unit_identity` and `decision_identity`. It is not an identity and is
authorized only in that branch. Included dispositions require lowercase
64-hex identities, and no other identity field accepts a sentinel.

## 6. Exact top-level topology

The closed readiness-record-v2 object contains exactly these 19 top-level
fields:

1. `readiness_identity`;
2. `schema`;
3. `experiment`;
4. `git_authority`;
5. `readiness_specification`;
6. `control_plane`;
7. `source_scopes`;
8. `protocol`;
9. `implementation`;
10. `execution_specification`;
11. `execution_profile`;
12. `runtime`;
13. `configuration`;
14. `external_inputs`;
15. `replay`;
16. `artifacts`;
17. `outcome_policy`;
18. `validation`; and
19. `attempt_policy`.

No other top-level field is permitted.

## 7. `schema`

The closed `schema` object contains exactly:

1. `canonical_encoding_revision`;
2. `declarations`; and
3. `schema_registry_identifier`.

`canonical_encoding_revision` is the governed readiness canonical-JSON
revision. `schema_registry_identifier` is exactly
`readiness-v1-schema-registry-v1`.

`declarations` contains exactly 29 closed objects, canonically ordered by
`object_kind`. Each declaration contains exactly:

1. `byte_count`;
2. `git_blob_identity`;
3. `object_kind`;
4. `path`;
5. `registry_identifier`;
6. `schema_id`; and
7. `sha256`.

`registry_identifier` is the short selected schema-policy identifier, such as
`readiness-record-v2`. `schema_id` is the schema document's exact JSON Schema
`$id`. Object kind, registry identifier, schema ID, and path are independently
unique. Every declaration MUST agree with the selected prospective 29-member
policy and the actual canonical schema bytes at `S`. In particular, that
policy selects readiness-record v2, adapter-declaration v3,
readiness-test-policy v2, profile-conformance-evidence v2, and the corrected
attempt-authority contract under their existing semantic kinds.

The readiness-record-v2 declaration binds an already-committed schema artifact
whose bytes exist independently of any record instance. It therefore creates
no identity self-reference.

## 8. `experiment`

The closed object contains exactly:

1. `canonical_record_path`;
2. `experiment_configuration_identity`; and
3. `experiment_identifier`.

The experiment identifier and canonical path satisfy v1.1 normalization. The
path is identity material and a later seal destination; Phase 3C candidate
validation MUST NOT write it.

## 9. `git_authority`

The closed object contains exactly:

1. `approved_branch_ref`;
2. `repository_authority_identifier`; and
3. `source_commit`.

All three MUST reconstruct from fresh Phase-2 repository authority and refer
to the same `S` used by every record section.

## 10. `readiness_specification`

The closed document binding contains exactly:

1. `byte_count`;
2. `git_blob_identity`;
3. `path`;
4. `revision`;
5. `sha256`; and
6. `specification_identity`.

It binds the frozen Execution Readiness v1.1 specification at `S`.

## 11. `control_plane`

The closed object contains exactly one field, `components`. `components` is
canonically ordered by `component_identifier`. Each closed component contains
exactly:

1. `component_identifier`;
2. `component_identity`;
3. `git_object_identity`;
4. `path`;
5. `role`; and
6. `sha256`.

There is exactly one component for each role token:

1. `adapter`;
2. `adapter_registry`;
3. `allocator_client`;
4. `allocator_contract`;
5. `canonical_serializer`;
6. `official_orchestrator`;
7. `outcome_gate`; and
8. `readiness_validator`.

The record does not choose any component identifier. The authoritative
identifier and path for every singleton role are exactly:

| Role | Authoritative component identifier | Authoritative path | Git object |
| --- | --- | --- | --- |
| `adapter` | selected adapter-v3 `adapter_identifier` | selected implementation binding `implementation.path` | regular blob, mode `100644` |
| `adapter_registry` | selected adapter-registry `registry_identifier` | `src/orev3/execution/registry.py` | regular blob, mode `100644` |
| `allocator_client` | selected attempt-authority contract `allocator_client_identifier` | `src/orev3/execution/attempts.py` | regular blob, mode `100644` |
| `allocator_contract` | selected attempt-authority contract `allocator_implementation_identifier` | `src/orev3/execution/attempts.py` | regular blob, mode `100644` |
| `canonical_serializer` | `canonical_serializer` | `src/orev3/execution/canonical.py` | regular blob, mode `100644` |
| `official_orchestrator` | `official_orchestrator` | `src/orev3/execution/orchestrator.py` | regular blob, mode `100644` |
| `outcome_gate` | `outcome_gate` | `src/orev3/execution/outcome_gate.py` | regular blob, mode `100644` |
| `readiness_validator` | `readiness_validator` | `src/orev3/execution/readiness.py` | regular blob, mode `100644` |

For a declaration-derived identifier, the identified committed declaration is
authoritative; for a fixed identifier, this table is authoritative. In both
cases validation reconstructs the expected identifier before reconstructing
the component identity. It then reads the exact path at `S`, requires the
listed regular-blob type and mode, verifies SHA-256 and Git object identity,
and derives `component_identity` with the existing domain
`orev3:readiness-control-component:v1\n` over the other five closed component
fields. A caller-selected safe identifier therefore cannot establish a
different component identity.

Control storage is not a ninth `control_plane.components` role. Its identifier,
path, blob, digest, and component identity are reconstructed from the closed
`control_storage_component` embedded in the prospective attempt-authority
contract, from its governed `control_plane` source scope, and from
`attempt_policy`. Adding it to this array would create a second representation
and would change the historically established eight-role vocabulary.

The following equalities are mandatory; none equates semantically different
identity domains:

| Repeated authority | Required equality/reconstruction |
| --- | --- |
| Adapter component | Its identifier and path equal the selected adapter-v3 identifier and implementation path; its blob and SHA-256 equal the implementation binding. Its control-component identity remains distinct from `adapter_identity` and `implementation_identity`. |
| Adapter registry component | Its identifier equals the selected registry identifier and its bytes equal the committed `registry.py`; its component identity remains distinct from `adapter_registry_identity`. |
| Allocator client | Its component identity equals `attempt_policy.allocator_client_component_identity` and the independently reconstructed attempt-authority value. |
| Allocator contract | Its control-component identity equals `attempt_policy.allocator_contract_identity` and the independently reconstructed attempt-authority value; it is not `allocation_authority_identity`. |
| Control storage | The embedded component identity equals `attempt_policy.control_storage_component_identity`; the same component is bound by `control_storage_contract_identity` and its exact source scope. |
| Outcome gate | The table-fixed committed component must be present. Outcome-aware profile authority must independently bind its governed authorization contract; characterization grants no route. Component and authorization-contract identities are not equal. |
| Source scopes | Every component path is covered by the uniquely matching governed scope, and its reconstructed path, blob/tree containment, mode, object identity, and `S` agree. |

Component presence and binding do not prove operational behavior, and
validation MUST NOT import or invoke a component.

## 12. `source_scopes`

`source_scopes` is an array of the existing governed source-scope branches.
Each top-level or containing declaration contains exactly:

1. `git_mode`;
2. `git_object_identity`;
3. `nesting`;
4. `repository_path`; and
5. `role`.

Each nested declaration additionally contains required `parent_path` and has
`nesting="nested"`.

Declarations are ordered by `repository_path`, then `role`. Repository paths
are unique. Paths, nesting, parent containment, Git mode, and object identity
MUST reconstruct at `S`.

The singleton roles are exactly:

- `execution_specification`;
- `implementation`;
- `protocol`;
- `readiness_schema`;
- `readiness_specification`;
- `readiness_test_policy`;
- `repository_authority`; and
- `source_tree`.

Duplicate bindings for a singleton role reject even when their paths and Git
objects differ. Repeated `configuration`, `control_plane`,
`dependency_manifest`, `readiness_tests`, and `runtime_manifest` roles remain
permitted when paths are distinct and all other closure rules hold.

## 13. `protocol`

The closed object contains exactly:

1. `byte_count`;
2. `git_blob_identity`;
3. `identifier`;
4. `path`;
5. `protocol_identity`;
6. `revision`; and
7. `sha256`.

## 14. `implementation`

The closed object contains exactly:

1. `adapter_identifier`;
2. `adapter_identity`;
3. `adapter_registry_identity`;
4. `entry_point`;
5. `implementation_git_blob_identity`;
6. `implementation_identity`;
7. `implementation_path`;
8. `implementation_sha256`;
9. `protocol_binding_byte_count`;
10. `protocol_binding_git_blob_identity`;
11. `protocol_binding_identity`;
12. `protocol_binding_path`; and
13. `protocol_binding_sha256`.

The registry, adapter-declaration-v3, implementation binding, implementation
blob, entry point, experiment, profile, configuration, protocol, and
attempt-output relationships MUST all reconstruct and agree at `S`. Caller
material cannot override a committed binding.

## 15. `execution_specification`

The closed document binding contains exactly:

1. `byte_count`;
2. `git_blob_identity`;
3. `path`;
4. `revision`;
5. `sha256`; and
6. `specification_identity`.

## 16. `execution_profile`

The closed object contains exactly:

1. `profile_identity`; and
2. `profile_name`.

Profile contracts and capability-specific evidence belong to
`outcome_policy`, not this section.

## 17. `runtime`

The closed object contains exactly:

1. `dependency_environment_identity`;
2. `dependency_lock_git_blob_identity`;
3. `dependency_lock_identity`;
4. `dependency_lock_path`;
5. `dependency_lock_sha256`;
6. `host_system_identity`;
7. `offline_artifact_manifest_git_blob_identity`;
8. `offline_artifact_manifest_identity`;
9. `offline_artifact_manifest_path`;
10. `offline_artifact_manifest_sha256`;
11. `python_implementation`;
12. `python_version`;
13. `runtime_bundle_identity`;
14. `runtime_contract_byte_count`;
15. `runtime_contract_git_blob_identity`;
16. `runtime_contract_identity`;
17. `runtime_contract_path`; and
18. `runtime_contract_sha256`.

These values are reconstructed from the committed runtime contract, dependency
lock, offline manifest, detached environment, and Phase-3A evidence for `S`.
They describe normalized detached-source authority, not launch-time machine
state. Credentials, ambient environment, and local mutable paths are excluded.

## 18. `configuration`

The closed object contains exactly:

1. `decision_selection_identity`;
2. `evidence_preparation_policy_identity`; and
3. `experiment_configuration_identity`.

`evidence_preparation_policy_identity` MUST equal the capability/resource
policy identity cross-bound by adapter-declaration-v3 and the Phase-3B
aggregate. Readiness-test-policy identity belongs only to `validation`.

## 19. `external_inputs`

The closed object contains exactly:

1. `dataset_validation_evidence_identities`;
2. `declarations`;
3. `input_snapshot_identities`; and
4. `projection_evidence_identities`.

### 19.1 Declarations

`declarations` uses the complete external-input declaration objects from the
selected adapter-declaration-v3. No second reduced declaration vocabulary is
created. Declarations are ordered by `role`, then their first normalized
`member_path`; external-input identifiers, roles where the selected adapter
declares them singleton, and first paths are unique.

Every declaration has these exact common fields:

1. `aggregate_byte_count`;
2. `external_input_identifier`;
3. `external_input_identity`;
4. `input_kind`;
5. `input_version`;
6. `members`;
7. `parser_configuration`;
8. `parser_configuration_identity`;
9. `parser_identity`;
10. `role`; and
11. `schema_identity`.

`external_input_identifier`, `input_version`, and `role` are nonempty NFC
tokens matching the repository safe-identifier grammar
`[a-z][a-z0-9_.-]*`; identities are lowercase 64-hex values. Byte counts are
nonnegative integers. Paths satisfy the common safe-path rule.
`aggregate_byte_count` equals the exact sum of member byte counts and, for a
regular file, equals its sole member's byte count.

Every member is closed and contains exactly:

1. `byte_count`;
2. `logical_identifier`;
3. `member_identity`;
4. `member_order`;
5. `member_path`; and
6. `sha256`.

`member_order` is a nonnegative integer and equals the member's zero-based
array position. Member paths, logical identifiers, and member identities are
independently unique. Each member identity uses domain
`orev3:readiness-adapter-external-input-member:v1\n` over the other five
member fields in the order listed above.

The closed `regular_file` branch has `input_kind="regular_file"`, contains
exactly one member, and that member has `member_order=0`. It has no manifest
field.

The closed ordered-manifest branch adds exactly these fields after the common
fields:

1. `manifest_identity`; and
2. `manifest_revision`.

It has `input_kind="ordered_file_collection"`, at least one member, and
`manifest_revision="external-input-ordered-file-manifest-v1"`. Its member
array is semantic manifest order and MUST NOT be value-sorted. The manifest
identity uses domain
`orev3:readiness-adapter-external-input-manifest:v1\n` over this exact closed
material, in the listed order:

1. `external_input_identifier`;
2. `input_version`;
3. `manifest_revision`; and
4. the complete ordered `members` array.

Duplicate members, path aliases, missing or extra members, and member
reordering reject. A regular-file object cannot carry manifest fields, and an
ordered-file collection cannot omit them.

The external-input identity retains the frozen domain
`orev3:readiness-adapter-external-input:v1\n`. Its material is the complete
closed branch, including all common fields and any manifest fields, excluding
only `external_input_identity`. Thus input kind, version, member identities
and order, manifest authority, parser configuration, parser component, role,
and schema all participate; two implementations do not choose a subset.

`parser_configuration` is closed and contains exactly:

1. `container`;
2. `decoder`;
3. `parser_identifier`;
4. `parser_revision`;
5. `record_ordering`; and
6. `schema_identity`.

`container`, `parser_identifier`, `parser_revision`, and `record_ordering`
are nonempty NFC safe-identifier tokens. The schema and parser identities are
lowercase 64-hex values.

Its identity uses domain
`orev3:readiness-adapter-parser-configuration:v1\n` over that entire object.
`parser_identifier` and `parser_revision` MUST equal the matching prospective
adapter-v3 dataset contract. `input_version` MUST equal that contract's
`dataset_version`. The identifier selects the finite committed
Phase-3B component policy; its path, revision, Git blob, digest, worker kind,
and component identity are reconstructed at `S`, and the result MUST equal
the declaration's `parser_identity`. `schema_identity` MUST equal the common
declaration field and reconstruct from the matching committed raw-schema
contract. `container` and `record_ordering` MUST equal the same dataset
contract.

`decoder` is a closed discriminated union. Uncompressed/direct parsing uses
exactly `{"decoder_kind":"not_required"}`. A container that requires a
decoder uses exactly these fields:

1. `configuration_byte_count`;
2. `configuration_git_blob_identity`;
3. `configuration_identity`;
4. `configuration_path`;
5. `configuration_sha256`;
6. `decoder_component_identity`;
7. `decoder_identifier`;
8. `decoder_kind`, fixed to `governed_decoder`;
9. `decoder_revision`;
10. `implementation_git_blob_identity`;
11. `implementation_path`; and
12. `implementation_sha256`.

The decoder configuration identity uses domain
`orev3:readiness-adapter-decoder-configuration:v1\n` over fields 1, 2, 4,
and 5. The decoder component identity uses the existing Phase-3B component
binding domain and exact identifier, revision, implementation path/blob/SHA,
and governed worker kind. Both blobs must be regular mode-`100644` objects at
`S`; both paths must be governed source scopes. An identifier or configuration
identity supplied only by the record is never authority.

Adapter v3 may declare only a decoder present in its finite committed
component policy. A container requiring a decoder cannot use `not_required`;
an uncompressed direct parser cannot carry decoder fields. These rules bind
exact bytes and configuration without importing or executing the parser or
decoder during record validation.

### 19.2 Evidence identity collections

`input_snapshot_identities` contains exactly one preparation snapshot identity
per external-input declaration in declaration order. Phase-3B aggregate
comparison independently normalizes the same identities as its governed
set-like collection before equality comparison.

`dataset_validation_evidence_identities` and
`projection_evidence_identities` are sorted unique identity collections.
Their membership MUST equal the applicable Phase-3B subordinate evidence and
its aggregate bindings. Profiles with zero inputs use four exact empty
collections where applicable; absence and `null` are invalid.

No Phase-3B evidence schema revision is required by adapter v3. The historical
immutable-input-snapshot schema already represents both `regular_file` and
`ordered_file_collection` and binds member order. Dataset identity
reconstruction already includes `external_input_identity`, dataset version,
container, parser component, schema, ordering, snapshot, and protocol even
though the normalized dataset-evidence object stores only its derived
`dataset_identity` and evidence identity. Prospective reconstruction MUST
recompute that identity with the v3 declaration, rather than trust the stored
hash. The Phase-3B aggregate independently binds the selected adapter identity
and subordinate identities. Consequently changed input version, manifest
order, parser configuration, decoder authority, or schema changes the v3
external-input identity and makes reconstructed dataset/aggregate authority
disagree. Existing evidence schemas need implementation support for the
already-governed collection branch, not a same-kind schema revision.

Prospective equality is exact: snapshot member `i` maps to declaration member
`i`; `logical_member_identifier` equals `logical_identifier`, `member_order`
equals `i`, and byte count and SHA-256 are equal. The snapshot's
`external_input_identifier` and `input_kind` equal the declaration. Dataset
identity is then recomputed with that snapshot identity and the v3
`external_input_identity`; parser and schema identities equal the declaration
and matching dataset contract; projection evidence, when required, binds the
same parser, dataset, snapshot, projector, and projection schema authority.
Thus the existing evidence objects carry sufficient derived authority without
embedding the expanded declaration or permitting identity-only acceptance.

Fresh prospective v1.1 Phase 3A/3B evidence MUST select adapter v3 and the v3
external-input declarations. Historical v1 evidence and frozen Slice-2 v2
evidence retain their original source policy and identities and are neither
recomputed nor relabeled.

This section contains preparation-time authority only. It contains no mutable
locator, current availability, launch snapshot, `current_external_inputs`, or
second-fetch state.

## 20. `replay`

The closed object contains exactly:

1. `candidate_order`;
2. `decision_selection_identity`;
3. `ordered_decision_identities`;
4. `ordered_replay_unit_identities`;
5. `ordered_source_unit_identities`;
6. `population_accounting`;
7. `projection_identity`;
8. `replay_evidence_identity`;
9. `replay_identity`;
10. `replay_preparer_component_identity`; and
11. `selector_component_identity`.

The three ordered identity collections preserve scientific construction order.
`replay_identity` is the first-order scientific Replay identity.
`replay_evidence_identity` is the identity of the normalized reconstruction
evidence. Neither may substitute for the other.

### 20.1 Population accounting

The closed embedded `population_accounting` object contains exactly:

1. `dispositions`;
2. `excluded_count`;
3. `included_count`;
4. `permitted_exclusion_reasons`;
5. `population_accounting_evidence_identity`; and
6. `source_count`.

Each disposition is one of exactly two closed branches, each containing
exactly `decision_identity`, `reason`, `replay_unit_identity`,
`source_unit_identity`, and `status`.

The included branch requires:

- `source_unit_identity`, `replay_unit_identity`, and `decision_identity` are
  lowercase 64-hex identities;
- `status="replay_included"`; and
- `reason="included_by_governed_selector"`.

The excluded branch requires:

- `source_unit_identity` is a lowercase 64-hex identity;
- `status="replay_excluded"`;
- `replay_unit_identity="not_applicable"`;
- `decision_identity="not_applicable"`; and
- `reason` is exactly one member of the selected adapter-v3 decision-selection
  contract's finite, sorted, unique `permitted_exclusion_reasons` collection.

An included branch cannot use a sentinel or an exclusion reason. An excluded
branch cannot use an arbitrary nonempty identity-like value, another sentinel,
or an ungoverned reason.

`dispositions` is source-order canonical, not value-sorted. It has exactly one
entry for each `ordered_source_unit_identities` entry, and disposition `i`
must have that source identity. Reading dispositions in that order:

1. included `replay_unit_identity` values produce exactly
   `ordered_replay_unit_identities`;
2. included `decision_identity` values produce exactly
   `ordered_decision_identities`;
3. excluded entries contribute to neither included array;
4. `source_count` equals both source-array and disposition length;
5. `included_count` equals the number of included entries and both included
   array lengths; and
6. `excluded_count` equals the number of excluded entries and
   `source_count-included_count`.

Duplicate, omitted, reordered, or extra source dispositions reject.
`permitted_exclusion_reasons` exactly equals the selected adapter-v3 contract
collection and remains sorted and unique. The embedded fields and the detached
population-accounting evidence MUST reconstruct the same evidence identity.

There is no second population identity and no outcome-bearing result.

## 21. `artifacts`

The closed object contains exactly:

1. `artifact_declaration_evidence_identity`;
2. `declarations`;
3. `dependency_order`; and
4. `output_policy_identity`.

`declarations` contains the complete selected adapter-declaration-v3 artifact
objects in canonical artifact-identifier order. Each contains exactly:

1. `artifact_identifier`;
2. `artifact_kind`;
3. `container`;
4. `declaration_identity`;
5. `dependencies`;
6. `dependency_roles`;
7. `execution_phase`;
8. `profile_applicability`;
9. `relative_path`; and
10. `schema_identity`.

Dependencies and dependency roles are canonical sorted unique collections.
`dependency_order` is produced by this exact deterministic algorithm:

1. Build a map keyed by NFC `artifact_identifier`; duplicate identifiers,
   duplicate declaration identities, duplicate or case-fold-colliding paths,
   and dependency edges to absent identifiers reject.
2. Compare identifiers by Unicode code-point order after NFC normalization.
3. Select traversal roots by iterating *all* artifact identifiers in that
   lexical order. This deliberately includes disconnected components and
   nodes that are also dependencies of another root.
4. Perform depth-first traversal. For a node, visit its dependency identifiers
   in their already-required sorted unique lexical order.
5. Emit a node only after every dependency has been emitted (postorder), so
   dependencies precede dependents.
6. A previously emitted node is skipped and is never emitted twice. Encounter
   of a node already on the active recursion stack is a cycle and rejects.
7. Continue the sorted root iteration until every declared node has been
   emitted exactly once.

The resulting postorder is the sole valid `dependency_order`; it is not
subsequently value-sorted. Consequently two independent roots cannot be
reversed merely because either order is topological. The declaration identity
sequence used by artifact evidence and the Slice-2 attempt-output declaration
is reconstructed from the declaration array in canonical artifact-identifier
order, while `dependency_order` uses the algorithm above. Every declaration
appears exactly once in both relevant representations, every edge is declared,
cycles reject, and no alternate declaration or traversal authority is
accepted.

## 22. Profile-conformance-evidence v2 branches

Profile-conformance-evidence v2 is a closed `oneOf` with exactly two branches.
Its stored `profile_conformance_evidence_identity` is excluded from its own
domain-separated identity material.

### 22.1 Characterization branch

The closed branch contains exactly:

1. `outcome_capability`;
2. `profile_conformance_evidence_identity`;
3. `profile_contract_identities`;
4. `profile_identity`;
5. `profile_name`;
6. `reconciled_artifact_declaration_identities`;
7. `schema_version`; and
8. `validated_artifact_identifiers`.

It requires:

- `schema_version=2`;
- `profile_name="outcome_blind_characterization_v1"`;
- `outcome_capability="prohibited_and_not_performed"`; and
- `profile_contract_identities=[]`.

No `authorization_contract_identity` field exists in this branch. No profile,
artifact, SHA-shaped sentinel, or other placeholder may substitute for one.

### 22.2 Outcome-aware branch

The closed branch contains exactly:

1. `authorization_contract_identity`;
2. `outcome_capability`;
3. `profile_conformance_evidence_identity`;
4. `profile_contract_identities`;
5. `profile_identity`;
6. `profile_name`;
7. `reconciled_artifact_declaration_identities`;
8. `schema_version`; and
9. `validated_artifact_identifiers`.

It requires:

- `schema_version=2`;
- `profile_name="outcome_aware_v1"`;
- `outcome_capability="outcome_aware_authorized_only"`;
- the exact six governed profile-contract identities ordered by their
  contract identifiers; and
- `authorization_contract_identity` equal to the governed authorization
  contract in that reconstructed set.

In both branches, `reconciled_artifact_declaration_identities` preserves
adapter artifact-declaration order and equals the applicable declarations.
`validated_artifact_identifiers` is sorted and unique. Neither branch contains
outcomes, labels, winners, results, interpretations, locators, or outcome
values.

## 23. `outcome_policy`

Readiness-record-v2 `outcome_policy` is a closed `oneOf` with exactly two
branches.

### 23.1 Characterization branch

The branch contains exactly:

1. `outcome_capability`;
2. `profile_conformance_evidence_identity`;
3. `profile_contract_identities`;
4. `profile_identity`; and
5. `profile_name`.

It requires the characterization profile, capability
`prohibited_and_not_performed`, and an exact empty contract-identity
collection. No authorization field or substitute exists.

### 23.2 Outcome-aware branch

The branch contains exactly:

1. `authorization_contract_identity`;
2. `outcome_capability`;
3. `profile_conformance_evidence_identity`;
4. `profile_contract_identities`;
5. `profile_identity`; and
6. `profile_name`.

It requires the outcome-aware profile, capability
`outcome_aware_authorized_only`, the six governed contract identities ordered
by contract identifier, and exact equality between
`authorization_contract_identity` and that set's authorization contract.

Both record branches MUST equal the independently reconstructed profile
identity and prospective profile-conformance-evidence-v2 material. They bind
authorization structure only; they grant no capability and carry no outcome
value.

## 24. `validation`

The closed object contains exactly:

1. `additional_test_selectors`;
2. `collected_node_ids`;
3. `compile_passed`;
4. `evidence_preparation_identity`;
5. `import_passed`;
6. `launch_smoke_selectors`;
7. `mandatory_test_selectors`;
8. `readiness_test_evidence_identity`;
9. `reconstruction_passed`;
10. `test_policy_identity`; and
11. `test_results`.

The three booleans are exactly `true` in a conforming candidate.
`test_policy_identity` is the reconstructed readiness-test-policy-v2 identity.
Mandatory and additional selectors, collected node IDs, and test results are
the canonical collections from the Phase-3B readiness-test evidence.
Selectors and node IDs are sorted and unique. `test_results` is ordered by
`node_id`, unique by `node_id`, and each closed result contains exactly
`node_id` and `status="passed"`.

`launch_smoke_selectors` equals the policy's canonical governed smoke subset.
It may be empty. It has no result field and is not executed during Phase 3A,
Phase 3B, or Phase 3C readiness candidate validation.

`evidence_preparation_identity` equals the complete Phase-3B aggregate
identity. Each direct record field is nevertheless independently reconstructed
from the applicable subordinate evidence and cross-checked against the
aggregate. The aggregate is not a second readiness identity.

## 25. `attempt_policy`

The closed object contains exactly:

1. `allocation_authority_identity`;
2. `allocator_client_component_identity`;
3. `allocator_contract_identity`;
4. `attempt_authority_contract_byte_count`;
5. `attempt_authority_contract_git_blob_identity`;
6. `attempt_authority_contract_path`;
7. `attempt_authority_contract_sha256`;
8. `attempt_identity_domain`;
9. `attempt_identity_schema_identifier`;
10. `attempt_output_declaration_identity`;
11. `collision_policy`;
12. `control_storage_component_identity`;
13. `control_storage_contract_identity`;
14. `output_namespace_identity_policy`;
15. `output_policy_identity`;
16. `output_policy_revision`; and
17. `supported_attempt_kinds`.

The attempt-authority contract path is exactly the governed prospective path
`config/research/readiness/attempt-authority-contract-v1.json`. Its actual
bytes, byte count, SHA-256, and Git blob at `S` are reconstructed.

`attempt_identity_domain` is exactly the governed attempt domain and
`attempt_identity_schema_identifier` is exactly the governed
attempt-identity-material schema-policy identifier. `collision_policy`,
output-namespace identity policy, output policy/revision, allocation authority,
allocator contract, allocator-client component, control-storage component and
contract, and attempt-output declaration MUST all equal their independently
reconstructed Slice-2 authority.

`control_storage_component_identity` is intentionally repeated as a direct
cross-check against the attempt-authority contract's committed component and
the control-storage-contract identity material. It does not identify a live
backend.

No intended-attempt-kind field is added. A conforming official readiness
candidate requires `supported_attempt_kinds` to contain `official`.
Structurally valid reusable contracts remain exactly official-only,
official-plus-reproduction, or reproduction-only; reproduction-only cannot
satisfy official candidate validation.

The section contains no ordinal, attempt identity, output-namespace identity,
allocation receipt, realized path, live availability, reservation, or
allocation result.

## 26. Evidence representation and reconstruction

Readiness-record v2 contains:

1. the direct normalized fields fixed in Sections 7 through 25; and
2. the subordinate evidence identities expressly fixed in those sections.

It MUST NOT embed complete Phase-3A or Phase-3B evidence objects. Complete
normalized evidence remains detached authority for `S`. Validation loads that
authority, validates it against the explicitly selected prospective overlays,
reconstructs its identities, and proves equality between its normalized
contents and every corresponding direct record field.

An aggregate identity alone is insufficient. Conversely, copying the complete
evidence objects into the record would create an unauthorized second transport
and duplicate canonical representation. This rule therefore preserves both
independent reconstruction and one record representation.

Preparation evidence remains distinct from later launch snapshots and current
input validation.

## 27. Readiness identity

The domain remains byte-for-byte:

```text
orev3:experiment-execution-readiness:v1\n
```

Let `M` be the complete readiness-record-v2 object containing the exact 18
sections above and excluding only the stored `readiness_identity`. Let `N` be
the canonical serialization of `M`, including its final LF. Then:

```text
readiness_identity = lowercase_hex(
  SHA256(UTF8("orev3:experiment-execution-readiness:v1\n") || N)
)
```

The stored identity MUST equal independent reconstruction. No other aggregate
readiness identity is permitted.

## 28. Acyclic identity graph

In this graph, `A -> B` means that `B` depends on or binds already-derived
`A`:

```text
repository authority + S
  -> schema documents and selected prospective 6/10/20/29 policies
  -> specification, protocol, and execution-specification bindings
  -> source scopes and committed control components

repository authority + S
  -> adapter registry
  -> adapter-declaration v3
  -> implementation/protocol binding

repository authority + S
  -> finite parser/decoder component policy + committed configuration
  -> parser/decoder component and configuration identities
  -> ordered member + manifest identities
  -> external-input declaration identities

repository authority + S
  -> runtime contract + dependency lock + offline manifest
  -> runtime/dependency-environment identities

repository authority + S
  -> experiment/decision/evidence policies
  + adapter-v3 external-input declarations
  -> immutable snapshots + dataset/projection evidence
  -> Replay scientific identity + Replay evidence
  -> source-ordered population dispositions + population accounting
  -> canonical artifact declarations + dependency postorder
  -> artifact evidence/output policy
  -> profile contracts + profile-conformance evidence v2

committed allocator component/contract
  -> allocator-contract identity

committed control-storage component
  -> control-storage-component identity
  -> control-storage-contract identity

allocation authority
+ allocator contract
+ control-storage contract
+ adapter-v3/output/artifact authority
  -> attempt-output declaration identity
  -> adapter identity

governed identifiers + committed component bytes at S
  -> exact control-plane component identities
  -> direct control-plane/attempt-policy/source-scope equalities

all reconstructed direct section material
+ all required subordinate evidence identities
  -> canonical readiness material M
  -> readiness_identity
```

The graph is acyclic because:

- schema documents are committed artifacts independent of record instances;
- readiness identity is derived last and is excluded from `M`;
- attempt-output material excludes adapter identity, while adapter identity may
  bind the already-derived attempt-output identity;
- external-input and parser/decoder identities are derived before the adapter
  identity that contains them, and none contains adapter or readiness identity;
- artifact dependency traversal consumes already-derived declarations and does
  not feed any identity back into those declarations;
- control-storage and allocator identities contain no readiness, attempt,
  namespace, allocation-receipt, or adapter identity;
- output-namespace identity and attempt identity are later lifecycle objects
  absent from the record; and
- Phase-3B aggregate and subordinate evidence contain no readiness identity.

## 29. Historical preservation and compatibility

This decision freezes that:

- historical readiness-record-v1 remains byte-identical and selected by
  historical Phase 2/3A/3B;
- historical profile-conformance-evidence-v1 remains byte-identical and
  selected by historical Phase 3B;
- historical adapter-declaration-v1 remains byte-identical;
- frozen Slice-2 adapter-declaration-v2 remains byte-identical under its
  original source authority and is not reinterpreted as complete v1.1 input
  authority;
- historical readiness-test-policy-v1 schema and configuration remain
  byte-identical;
- historical evidence remains governed by its original source authority and is
  never recomputed, repaired, or relabeled;
- prospective post-governance overlays explicitly select readiness-record v2,
  adapter-declaration v3, readiness-test-policy v2, and
  profile-conformance-evidence v2 at the applicable 6/10/20/29 levels;
- the corrected attempt-authority contract remains under its existing kind;
  and
- schema-kind counts remain historical 6/10/20 and prospective 6/10/20/29.

## 30. Phase 3C and lifecycle boundary

This decision does not expand Phase 3C. Phase 3C ends at deterministic
canonical candidate bytes, independently reconstructed `readiness_identity`,
and authoritative `READINESS_VALIDATED`, or canonical outcome-free
`READINESS_REJECTED`.

This decision does not authorize or implement:

- candidate persistence or writing the canonical record path;
- seal `R` or current-readiness resolution;
- `EXECUTION_READY`;
- launch, second-fetch processing, or smoke execution;
- allocation, ordinal consumption, namespace identity or realization;
- allocation receipts or control records;
- backend access, availability, atomicity, fencing, persistence, or recovery;
- ranking, outcome authorization execution, evaluation, or experiment
  execution;
- outcome, label, winner, result, or interpretation flow into readiness; or
- Experiment 5, scientific research, miner work, wallet work, or transactions.

Slice 3 may validate and reconstruct a complete readiness-record candidate
supplied as canonical data. It MUST NOT assemble that candidate from Phase-3B
evidence, mint lifecycle authority, or create a production happy path.

## 31. Implementation consequences

After this decision is reviewed and frozen, Slice 3 implementation may:

1. add readiness-record-v2, profile-conformance-evidence-v2, and
   adapter-declaration-v3 schemas;
2. add explicit prospective substitutions under the existing semantic kinds;
3. preserve all historical policies and schema bytes;
4. implement the exact closed field validation above;
5. reconstruct every Git, schema, contract, component, evidence, and identity
   binding at `S`;
6. cross-check direct record fields against detached Phase-3B evidence;
7. reproduce the single readiness identity; and
8. add focused structural, reconstruction, substitution, and preservation
   tests, including identifier substitution, control/attempt cross-section
   mismatches, both external-input branches, member/version/parser-config
   substitutions, both disposition branches and positional reconciliation,
   independent-root artifact ordering, cycles, and v1/v2/v3 adapter selection.

Phase-3B implementation may add prospective adapter-v3 loading and ordered
collection handling, but it MUST use the existing evidence schema revisions
for the reasons in Section 19.2. It may not relabel historical evidence or
mutate adapter v1, adapter v2, or any historical evidence schema.

No implementation may infer a different nesting, omit a required field, embed
complete evidence objects, introduce a second readiness identity, add a
thirtieth kind, or silently fall back to a historical revision.

## 32. Self-review result

The decision has been checked against the following failure modes:

- historical schema mutation: prohibited by explicit revision substitution;
- duplicate semantic kinds: one selected revision per kind;
- registry-count growth: no new kind, counts remain 6/10/20/29;
- characterization authorization placeholder: eliminated prospectively;
- outcome leakage: no outcome-bearing value is permitted;
- schema self-reference: schema artifacts precede record instances;
- identity cycles: readiness identity is derived last and later lifecycle
  identities do not feed backward;
- identity-only authority: direct fields are independently reconstructed;
- evidence duplication: complete evidence remains detached;
- ambient revision choice: explicit overlay selection is mandatory;
- arbitrary control identifier: prohibited by the role table and independent
  declaration/fixed-token reconstruction;
- control/attempt disagreement: prohibited by the equality matrix;
- regular-file versus ordered-manifest ambiguity: eliminated by closed,
  disjoint adapter-v3 branches;
- member, input-version, parser-configuration, or decoder substitution: bound
  into independently reconstructed declaration material;
- population sentinels or arbitrary exclusion reasons: eliminated by exact
  branches and finite governed vocabulary;
- omitted, extra, duplicate, or reordered population dispositions: rejected
  by positional reconciliation;
- independent artifact-root reordering and artifact cycles: rejected by the
  exact sorted-root depth-first postorder algorithm;
- historical adapter selection: v1, frozen v2, and prospective v3 authority
  are explicit and never discovered ambiently;
- live backend or launch authority: expressly excluded; and
- unresolved canonical representation choices: the field sets, branches,
  evidence rule, registry identifier, attempt-kind rule, and identity DAG are
  fixed above.

The bounded convergence attacks have these governed results:

| Attack | Required result |
| --- | --- |
| Same control role/path/blob with another identifier | reject against the role table before accepting the derived identity |
| Allocator component disagreement between sections | reject under the equality matrix |
| Control-storage component disagreement | reject against the attempt-authority component, contract material, scope, and `attempt_policy` |
| Closed regular-file declaration | accept when its sole member and every reconstructed binding agree |
| Closed ordered-manifest declaration | accept when manifest order and every reconstructed binding agree |
| Reordered manifest members | reject; order changes member order, manifest identity, external-input identity, and evidence reconciliation |
| Changed input version | reject; version changes external-input and reconstructed dataset authority |
| Changed parser/decoder configuration | reject; configuration and external-input identities change |
| Arbitrary excluded Replay or decision identity | reject; only `not_applicable` is permitted |
| Unsupported exclusion reason | reject against the finite adapter-v3 vocabulary |
| Omitted or extra population disposition | reject under positional/count reconciliation |
| Independent artifact roots reversed | reject against sorted-root DFS postorder |
| Artifact cycle | reject on active-stack encounter |
| Historical adapter v1 reconstruction | select v1 only under historical Phase 3A/3B policy |
| Frozen adapter v2 reconstruction | select v2 only under its frozen Slice-2 source policy |
| Fresh complete-v1.1 adapter reconstruction | select v3 explicitly |
| Registry substitutions | retain one revision per kind and counts 6/10/20/29 |
| Outcome or later-lifecycle data insertion | reject as unknown/out-of-scope material |

No additional normative choice is intentionally left to Slice 3
implementation.
