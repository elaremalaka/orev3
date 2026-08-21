# ORE Miner V3 — Execution Readiness Phase 3C Intermediate Checkpoint

## 1. Purpose and authority

This is an intermediate continuation and navigation checkpoint. It is not a
replacement specification, governance decision, protocol, schema, finding, or
implementation authority. If this summary conflicts with a primary governing
source, the primary source controls.

This document becomes the current Execution Readiness continuation checkpoint
only when its exact bytes are committed, pushed to `origin/research/post-v1`,
and independently verified there. Until then, the historical Phase 3B handoff
remains the latest tracked continuation checkpoint.

The repository state immediately before creating this checkpoint was:

| Property | Value |
| --- | --- |
| Branch | `research/post-v1` |
| Pre-checkpoint HEAD | `ace3d3257d2579d839c47f06f2650da36215496c` |
| Tracking HEAD | `ace3d3257d2579d839c47f06f2650da36215496c` |
| Independently queried remote HEAD | `ace3d3257d2579d839c47f06f2650da36215496c` |
| Ahead / behind | `0 / 0` |
| Index | clean |
| Working tree | active uncommitted Slice-2 work plus 28 preserved unrelated paths |
| Unrelated-work fingerprint | `01d0f934e07f2c4955752fcd1603274c989a6abf1168501b5e21184dc53ec001` |

All pre-existing working-tree content is preserved. Its presence is not
authority, and this checkpoint does not adopt or absorb it.

## 2. Historical continuation chain

The continuation chain is:

| Milestone | Commit | Status |
| --- | --- | --- |
| Phase 3B handoff | `4bfd568bbeabc58aa400b2b7c3ad4d0e12be4434` | historical, frozen, pushed, remote-backed |
| V1.1 governance and specification | `f7e09f0e2c24f17dedca879c817ae3c78cda7026` | frozen, pushed, remote-backed |
| Phase 3C Slice 1 | `d1580d5aca721eca6a79129ceac04926a1daabd4` | frozen, pushed, remote-backed |
| Readiness-test-policy v2 versioning governance | `ace3d3257d2579d839c47f06f2650da36215496c` | frozen, pushed, remote-backed |

The [Phase 3B handoff](ore-v3-execution-readiness-phase3b-handoff.md) remains
an immutable historical navigation document. The v1.1 governance/specification
freeze and Slice 1 supersede its earlier frozen-v1 assumptions only for fresh
prospective v1.1 work; they do not rewrite its historical record.

After this checkpoint is successfully frozen and remotely verified, it becomes
the current continuation checkpoint. All earlier milestones remain historical.

## 3. Frozen v1.1 authority

The governing prospective authority is:

| Authority | Path | SHA-256 |
| --- | --- | --- |
| Experiment Execution Readiness v1.1 | [`docs/research/specifications/experiment-execution-readiness-v1.1.md`](../research/specifications/experiment-execution-readiness-v1.1.md) | `e938499cc254ce2d65fce925fb6e33c5d8b9dcea73a91a2c01e1017e8fb17da9` |
| Clarification governance | [`docs/research/governance/execution-readiness-v1-clarification-decision.md`](../research/governance/execution-readiness-v1-clarification-decision.md) | `ce9e7cd57df0d31db5aea0c7674edc3b3b717b96a790d5c7e3075364df151477` |
| Readiness-test-policy v2 versioning governance | [`docs/research/governance/execution-readiness-v1.1-readiness-test-policy-versioning.md`](../research/governance/execution-readiness-v1.1-readiness-test-policy-versioning.md) | `e0d79b517b126633bb2f39448c61a84307dfd3b51628a39c8501eb7653fe20fd` |

These documents remain immutable. This checkpoint records their continuation
effect but does not modify, reinterpret, or replace them.

## 4. Phase 3C boundary

Phase 3C ends at one of the two authoritative branches defined by v1.1:

```text
deterministic canonical readiness-record candidate bytes
  + readiness_identity
  -> READINESS_VALIDATED
```

or canonical outcome-free `READINESS_REJECTED` when a prerequisite fails and
canonical rejection-receipt production succeeds. The separately governed
`CANONICAL_RECEIPT_UNAVAILABLE` abort establishes neither branch and advances
no lifecycle state.

Phase 3C remains before:

- candidate persistence or canonical readiness-path materialization;
- seal `R`;
- current-readiness resolution;
- launch or launch-authority snapshots;
- smoke execution;
- attempt or ordinal allocation;
- namespace realization;
- `STARTED`, terminal records, recovery, or the control lifecycle;
- ranking or ranking freeze;
- outcome-authorization execution or outcome opening;
- evaluation; and
- experiment execution.

## 5. Phase 3C Slice 1 status

Commit `d1580d5aca721eca6a79129ceac04926a1daabd4` is the frozen, pushed, and
remote-backed Phase 3C Slice-1 schema-foundation authority.

Slice 1 established:

- the final prospective v1.1 registry of exactly 29 semantic object kinds;
- preservation of the historical Phase 2, Phase 3A, and Phase 3B registry
  progression of exactly 6, 10, and 20 members;
- the reviewed schema foundation for the nine v1.1 additions; and
- the recursively fail-closed canonical schema validator foundation.

Slice 1 passed adversarial review, bounded corrections, targeted verification,
and remote-backed freeze. It must not be reopened merely to simplify later
implementation.

## 6. Readiness-test-policy versioning status

Commit `ace3d3257d2579d839c47f06f2650da36215496c` froze and remotely backed the
readiness-test-policy v2 compatibility decision.

That decision preserves:

- immutable historical readiness-test-policy v1 schema, policy, evidence, and
  Phase 2/3A/3B registry authority;
- prospective v1.1 use of readiness-test-policy v2;
- explicit prospective overlays of exactly 6, 10, 20, and 29 members;
- substitution under the same semantic object kind,
  `readiness-test-policy`; and
- no thirtieth registry member.

Smoke selectors are bound during prospective preparation and readiness
validation but are not executed during Phase 2, Phase 3A, Phase 3B, or Phase
3C.

## 7. Current Slice-2 implementation state

Phase 3C Slice 2 is **implemented locally but NOT frozen, NOT committed, and
NOT authoritative**. Its bounded purpose is deterministic governed loading,
reconstruction, explicit generation selection, and cross-validation of the
prerequisite contracts needed by later candidate construction.

The current local Slice-2 paths, recorded from Git state, are:

```text
 M src/orev3/execution/readiness_record.py
 M tests/execution/test_readiness_record.py
?? config/research/readiness/readiness-test-policy-v2.json
?? src/orev3/execution/readiness_contracts.py
?? src/orev3/execution/schemas/v1/readiness-test-policy-v2.schema.json
?? tests/execution/test_phase3c_readiness_contracts.py
```

These files remain unstaged. Their current bytes must be preserved while the
remaining authority questions are resolved. This checkpoint neither reviews
nor adopts those bytes.

## 8. Slice-2 adversarial-review status

The Slice-2 adversarial review found no BLOCKER, three HIGH findings, and one
MEDIUM finding:

1. **HIGH — launch-smoke mandatory subset:**
   `launch_smoke_selectors` must be constrained to the governed mandatory
   readiness selector set; syntactic validity alone cannot establish smoke
   authority.
2. **HIGH — control-storage authority:**
   `control_storage_contract_identity` lacks frozen reconstructable identity
   semantics and currently cannot be accepted merely because it is SHA-shaped.
3. **HIGH — attempt-output authority:**
   `attempt_output_declaration_identity` lacks frozen reconstructable identity
   semantics and currently cannot be accepted merely because it is SHA-shaped.
4. **MEDIUM — duplicate singleton roles:** duplicate singleton source-scope
   authority roles must fail even when their paths and Git objects are
   individually valid, while legitimate multi-path roles remain supported.

The bounded correction stopped under its explicit authority-gap rule rather
than inventing either missing identity model.

## 9. Authority-gap investigation result

### 9.1 Control storage

No existing identity is semantically exact for the separately named
`control_storage_contract_identity`:

- `allocation_authority_identity` identifies the configured shared authority
  instance, including its permanent ledger and control-storage authority;
- `allocator_contract_identity` identifies reusable allocation semantics and
  implementation bindings; and
- control-component identity identifies committed implementation bytes, not a
  complete control-storage contract.

Multiple models therefore remain possible under the frozen text. The
recommended model is a distinct reusable control-storage contract identity
represented by closed material within the prospective
`attempt-authority-contract`. Its exact canonical material, domain, component
binding, and cross-binding are recommendations only until new governance
freezes them.

No new top-level schema-registry kind is currently expected.

### 9.2 Attempt output

`attempt_output_declaration_identity` is not semantically equivalent to the
existing `output_policy_identity`. The latter identifies generic governed
output-policy semantics and does not independently bind an adapter,
experiment, attempt authority, allocator contract, namespace policy, or the
complete artifact declaration set.

The recommended model is an adapter-specific attempt-output declaration
identity binding the existing output-policy authority with the selected
adapter/experiment, attempt authority, allocator contract, namespace policy,
and artifact/output declarations. Its exact canonical material, domain, and
cross-bindings remain recommendations until governed.

The historical `adapter-declaration` schema is already bound by Phase 3A and
Phase 3B authority and must not be mutated in place. The expected compatibility
mechanism is a prospective `adapter-declaration` v2 revision selected under the
same semantic object kind. Its exact coordinates require governance.

No new top-level schema-registry kind is currently expected.

### 9.3 Registry consequence

The prospective final registry is expected to remain exactly 29 kinds.
Closed embedded identity material does not automatically require a top-level
schema kind, and a prospective adapter-declaration revision can substitute
under the existing semantic kind while historical registries retain v1.

## 10. Exact next task

After this checkpoint is frozen, the next task MUST be:

> **Create one narrow governance decision resolving both Slice-2 prerequisite
> authority identities together.**

That decision must freeze:

- control-storage identity semantics;
- exact control-storage canonical material and identity domain;
- attempt-output declaration semantics;
- exact attempt-output canonical material and identity domain;
- prospective adapter-declaration v2 coordinates and explicit overlay
  selection;
- the prospective attempt-authority schema correction;
- every required cross-binding;
- one complete acyclic identity DAG;
- historical schema/evidence preservation; and
- the unchanged 29-kind registry.

Do not substitute another investigation unless repository authority materially
contradicts the findings recorded here. Do not implement either recommended
identity model before that governance is reviewed and frozen.

## 11. Intended continuation after the governance decision

The intended sequence is:

1. perform a targeted read-only review of the single governance decision;
2. freeze, push, and remotely verify that decision;
3. resume the preserved Slice-2 correction;
4. enforce the launch-smoke mandatory-subset relationship;
5. implement the two clarified identity reconstructions and cross-bindings;
6. enforce singleton source-scope role uniqueness without restoring the old
   blanket singleton-path limitation;
7. perform targeted Slice-2 verification;
8. freeze, push, and remotely verify Slice 2; and
9. proceed to Slice 3 under the resulting governing source commit.

No step in this sequence authorizes candidate construction, launch, outcomes,
scientific execution, Experiment 5, mining, wallet operations, transactions,
or real-SOL work.

## 12. Long-term checkpoint rule

This is an **intermediate** checkpoint only.

When the full Experiment Execution Readiness implementation is complete,
reviewed, frozen, pushed, and remote-backed, a new comprehensive tracked
project checkpoint MUST be created before research resumes or work proceeds
further toward the miner.

That future comprehensive checkpoint will supersede this intermediate
checkpoint as the current continuation checkpoint. The Phase 3B handoff and
this intermediate checkpoint will remain immutable historical navigation
documents.
