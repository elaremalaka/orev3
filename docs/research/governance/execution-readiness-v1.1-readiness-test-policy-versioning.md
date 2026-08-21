# Execution Readiness v1.1 Readiness-Test-Policy Versioning Decision

## Decision status

- Decision identifier: `execution-readiness-v1.1-readiness-test-policy-versioning`
- Decision type: repository compatibility and versioning governance
- Status: proposed for targeted review
- Governing branch: `research/post-v1`
- Governing source commit: `d1580d5aca721eca6a79129ceac04926a1daabd4`
- Governing specification: [Experiment Execution Readiness v1.1](../specifications/experiment-execution-readiness-v1.1.md)
- Governing specification revision: `experiment-execution-readiness-v1.1`
- Governing specification SHA-256: `e938499cc254ce2d65fce925fb6e33c5d8b9dcea73a91a2c01e1017e8fb17da9`
- Prior clarification decision: [Execution Readiness v1 Clarification Decision](execution-readiness-v1-clarification-decision.md)
- Prior clarification-decision SHA-256: `ce9e7cd57df0d31db5aea0c7674edc3b3b717b96a790d5c7e3075364df151477`
- Implementation authorized by this document: no
- Execution-readiness lifecycle semantic change: none

This decision freezes the repository-level compatibility mechanism required to represent the already-governed `launch_smoke_selectors` field without mutating historically bound schema or policy bytes. It does not reopen or alter the normative lifecycle, authority, identity, outcome, or information-flow semantics of the governing specification.

## 1. Blocker and decision scope

The governing specification requires the repository-owned readiness-test policy used prospectively by v1.1 to declare `launch_smoke_selectors`. The historical `readiness-test-policy` schema is closed and does not admit that field. Its exact bytes are already bound by historical Phase 2, Phase 3A, and Phase 3B authority.

The historical schema and policy therefore MUST NOT be modified, relabeled, or reinterpreted. A prospective schema and policy revision MUST represent the v1.1-required field. This is a compatibility and versioning decision only; it does not change when smoke selectors are bound or when launch smoke may execute.

## 2. Historical revision remains immutable

The historical readiness-test-policy authority remains exactly:

| Coordinate | Frozen value |
|---|---|
| Semantic object kind | `readiness-test-policy` |
| Registry identifier | `readiness-test-policy-v1` |
| Schema `$id` | `orev3://schemas/execution-readiness/v1/readiness-test-policy` |
| Schema path | `src/orev3/execution/schemas/v1/readiness-test-policy.schema.json` |
| Schema version | `1` |
| Schema SHA-256 | `1aac9f934c4d58274578519098d1b1762637a3e77902d0b43dd2fef4866f8886` |
| Policy path | `config/research/readiness/readiness-test-policy-v1.json` |
| Policy identifier | `experiment-execution-readiness-phase2-tests-v1` |
| Policy identity | `e2eff3859d6400ca7b4dde0528900055b377cc40c4561fece8ec259af7d34720` |
| Policy-file SHA-256 | `918772c164dc0686fae8d8b284698ae43afe514e52a38625b3f5c1ec91747572` |

Historical Phase 2, Phase 3A, and Phase 3B schema registries, loaders, reconstruction paths, evidence, and checkpoints MUST continue to bind these exact historical objects. Historical evidence MUST retain its original readiness-test-policy identity and source authority. It MUST NOT be recomputed, relabeled, repaired, or interpreted as evidence produced under the prospective revision.

## 3. Prospective v1.1 schema revision

The prospective schema revision is frozen as:

| Coordinate | Governed value |
|---|---|
| Semantic object kind | `readiness-test-policy` |
| Registry identifier | `readiness-test-policy-v2` |
| Schema `$id` | `orev3://schemas/execution-readiness/v1/readiness-test-policy-v2` |
| Schema path | `src/orev3/execution/schemas/v1/readiness-test-policy-v2.schema.json` |
| Schema title | `ReadinessTestPolicyV2` |
| Schema version | `2` |

The v2 schema MUST retain the historical governed readiness-test-policy fields and MUST add the required `launch_smoke_selectors` field. `launch_smoke_selectors` MUST be a canonical collection: its members MUST be sorted in canonical order and unique. The collection MAY contain exactly zero members. Missing and empty are distinct: because the field is governed, an empty selector set MUST be represented by the present canonical empty collection rather than by an omitted or null field.

The v2 schema remains closed and MUST preserve the governed selector syntax and safety constraints applicable to repository-owned readiness-test selectors. The v2 schema bytes do not yet exist. This decision therefore MUST NOT state or anticipate their content SHA-256 or Git blob identity.

## 4. Prospective v1.1 policy revision

The prospective policy revision is frozen as:

| Coordinate | Governed value |
|---|---|
| Policy path | `config/research/readiness/readiness-test-policy-v2.json` |
| Policy identifier | `experiment-execution-readiness-v1.1-tests-v1` |
| Schema version | `2` |
| Policy identity domain | `orev3:readiness-test-policy:v1\n` |

The policy identity domain remains unchanged. The changed canonical policy material, including the schema-version and `launch_smoke_selectors` bindings, produces a distinct policy identity under the existing domain-separated identity algorithm. The v2 policy bytes do not yet exist. This decision therefore MUST NOT state or anticipate their content SHA-256, Git blob identity, or derived policy identity.

## 5. Registry substitution and fixed counts

Historical generation-specific registries MUST continue to bind the v1 readiness-test-policy member. Prospective v1.1 registries MUST substitute the v2 member for the v1 member under the same semantic object kind, `readiness-test-policy`.

The substitution rule is exact:

| Registry authority | Readiness-test-policy member | Member count |
|---|---|---:|
| Historical Phase 2 | `readiness-test-policy-v1` | 6 |
| Historical Phase 3A | `readiness-test-policy-v1` | 10 |
| Historical Phase 3B | `readiness-test-policy-v1` | 20 |
| Prospective v1.1 Phase 2 overlay | `readiness-test-policy-v2` | 6 |
| Prospective v1.1 Phase 3A overlay | `readiness-test-policy-v2` | 10 |
| Prospective v1.1 Phase 3B overlay | `readiness-test-policy-v2` | 20 |
| Prospective v1.1 final registry | `readiness-test-policy-v2` | 29 |

One registry MUST contain exactly one member for the semantic object kind `readiness-test-policy`. The prospective v1.1 29-member registry MUST NOT contain both readiness-test-policy revisions. It MUST replace the historical member with the prospective member and MUST remain exactly 29 members. This decision creates neither a thirtieth registry member nor a new semantic object kind.

The repository MAY contain both schema files and both policy files. Repository file existence and selected registry membership are distinct facts. The existence of both revisions MUST NOT create duplicate object-kind authority within a selected registry.

Current registry machinery may continue to key one selected schema declaration by semantic object kind. It MUST represent revision selection through an explicit historical-generation policy or prospective-v1.1 overlay, not through two simultaneous entries having the same key.

## 6. Prospective generation overlays

Historical generation policies are the immutable policies used to reconstruct historical Phase 2, Phase 3A, and Phase 3B evidence. Prospective v1.1 generation overlays are separate explicit selections used to construct fresh Phase 2, Phase 3A, and Phase 3B evidence for a future source commit `S` governed by v1.1.

The prospective overlays MUST substitute the v2 readiness-test-policy schema member consistently at the 6-, 10-, 20-, and 29-member levels. Apart from this governed substitution, each overlay MUST preserve the membership and ordering semantics of its corresponding generation policy. The overlays remain keyed by the same semantic object kind and MUST NOT relabel or mutate any historical registry or evidence.

## 7. Deterministic selection

Historical APIs and historical reconstruction MUST explicitly select the historical generation policies and the v1 readiness-test-policy objects.

Future Phase 3C and v1.1 prospective preparation MUST explicitly select the prospective v1.1 generation overlay and the v2 readiness-test-policy objects. The selected authority generation and readiness-test-policy revision MUST be explicit and deterministic in the governed execution path.

Selection MUST NOT depend on:

- ambient filesystem contents;
- whichever schema or policy file happens to exist;
- filename enumeration order;
- a mutable “latest” alias;
- caller-supplied schema or policy authority;
- an implicit fallback between v1 and v2.

A missing selected member, a mismatched revision, a mismatched schema identity, a mismatched source binding, or an inconsistent overlay MUST fail closed. A loader MUST NOT fall back to the other revision.

## 8. Evidence compatibility

The `readiness-test-evidence` schema and identity domain do not change. The `evidence-preparation` schema and identity domain do not change.

Fresh Phase 2, Phase 3A, and Phase 3B evidence constructed prospectively under v1.1 MUST bind:

- the new readiness-test-policy identity derived from the exact v2 policy material;
- the selected prospective overlay and its v2 schema declaration;
- the future source commit `S` containing the exact selected schema, policy, configuration, and implementation bytes.

Historical evidence MUST retain its original policy identity, historical registry authority, and historical source authority. Fresh prospective evidence and historical evidence are distinguished by their actual governed bindings; neither is relabeled as the other.

`launch_smoke_selectors` are bound by readiness-test-policy authority during prospective preparation and readiness validation. They MUST NOT be executed during Phase 2, Phase 3A, Phase 3B, or Phase 3C. Launch-smoke execution remains a later launch-time operation after current readiness and the other governing launch preconditions.

## 9. Source and reconstruction requirements

For a future v1.1 source commit `S`, governed source scopes MUST include the selected v2 schema path, v2 policy path, and every committed implementation or configuration path required to load, validate, and reconstruct them. Trust-bearing validation MUST reconstruct those objects from safe regular Git blobs at detached `S`, validate the selected registry declaration and policy material, and cross-bind the resulting identities.

The presence of a v2 file in an ambient working tree is not authority. Missing, unsafe, malformed, wrong-Git, or cross-source substituted objects MUST fail closed.

## 10. Implementation consequences

Later implementation work is required to add the exact v2 schema and policy bytes, their prospective registry declarations and generated digests, explicit prospective overlay selection, Git reconstruction, source-scope bindings, cross-validation, and focused tests. That work MUST preserve the historical schema and policy bytes and all historical registry constants.

This document does not authorize implementation and does not define final schema or policy content digests. Exact digests and derived identities become authoritative only after the corresponding bytes exist and are reviewed under the governed freeze process.

## 11. Non-goals and unchanged boundaries

This decision does not authorize or alter:

- readiness-test or launch-smoke execution timing;
- launch-smoke execution during preparation or Phase 3C;
- readiness-candidate construction;
- `READINESS_VALIDATED` or `EXECUTION_READY`;
- launch or current-readiness resolution;
- attempt or ordinal allocation;
- output-namespace realization;
- control-record creation or recovery;
- ranking or ranking freeze;
- outcome authorization or outcome access;
- evaluation or experiment execution;
- the production adapter registry;
- the 29-kind vocabulary;
- the normative semantics of frozen v1.1.

The production adapter registry remains empty unless separately populated by future governed implementation authority. This decision does not supply or authorize a placeholder adapter, allocator, orchestrator, or outcome gate.

## 12. Required conformance regressions

Future implementation conformance MUST prove at least:

1. historical schema and policy bytes and identities remain unchanged;
2. historical 6-, 10-, and 20-member registries select `readiness-test-policy-v1`;
3. prospective v1.1 6-, 10-, 20-, and 29-member overlays select `readiness-test-policy-v2`;
4. every selected registry contains exactly one `readiness-test-policy` member;
5. the prospective v1.1 registry remains exactly 29 members;
6. the v2 schema requires a present canonical `launch_smoke_selectors` collection;
7. canonical empty `launch_smoke_selectors` is accepted and missing, null, unsorted, or duplicate selector collections are rejected;
8. historical reconstruction cannot select v2 and prospective reconstruction cannot silently fall back to v1;
9. selection is explicit and unaffected by the simultaneous repository presence of both revisions;
10. fresh evidence binds the v2 policy identity and future `S`, while historical evidence retains its original bindings;
11. neither preparation nor Phase 3C executes launch smoke;
12. no thirtieth registry member or alternate semantic object kind is introduced.

## 13. Self-review and normative closure

This decision preserves the historical schema and policy bytes, historical generation-specific registry authority, historical evidence identities, and the frozen v1.1 lifecycle. It introduces no duplicate object kind within a selected registry, no ambient revision selection, no readiness-test-evidence identity change, and no preparation-time smoke execution.

The frozen authority permits this single deterministic compatibility mechanism: revisioned repository objects are selected by explicit generation authority, while the prospective registry substitutes the revision under the existing semantic object kind. No additional normative choice remains within the scope of this versioning blocker.
