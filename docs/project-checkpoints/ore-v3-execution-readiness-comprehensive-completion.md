# ORE Miner V3 — Execution Readiness Comprehensive Completion Checkpoint

Status: Draft — ready for targeted review

This checkpoint records the completed Execution Readiness implementation boundary through `EXECUTION_READY` at governing source commit `7ba0bcc443e5efb7b7945c209c4f7fce46a06898` on `research/post-v1`. All Phase-3C implementation slices through Slice 5 are reviewed, frozen, pushed, and independently remote-backed.

This draft does not become active continuation authority until it is itself reviewed, frozen, committed, pushed, and independently remote-verified. Once that occurs, it supersedes the [Phase-3B handoff](ore-v3-execution-readiness-phase3b-handoff.md) and [Phase-3C intermediate checkpoint](ore-v3-execution-readiness-phase3c-intermediate.md) for ordinary continuation. Those older checkpoints remain immutable historical authority; supersession for continuation does not delete, rewrite, invalidate, or reinterpret them.

This checkpoint does **not** claim launch readiness, miner completion, live-capital readiness, or authorization to spend real SOL.

## 1. Project orientation

The architectural direction remains:

```text
Observer
  → Historical Dataset
  → Replay Engine
  → Strategy Lab
  → Decision Engine
  → Portfolio Simulator
  → Paper Miner
  → Live Miner
  → Adaptive Strategy
```

The evolved objective is to build a miner that can eventually be trusted to operate with real SOL. Research, replay, governed experiments, simulation, paper mining, Execution Readiness, and later lifecycle controls must establish evidence, correctness, and safety before real-capital deployment. That objective has not yet been achieved.

Experiments 1–4 remain prior research history. Experiment 4's official governed execution was valid but produced negative evidence: Deployment-per-Miner was not supported as a predictive winner-ranking signal at the tested decision point. The standing decision after Experiment 4 was to stop further signal experiments until a durable Execution Readiness workflow was implemented and adopted. Execution Readiness was therefore infrastructure and governance work required before scientific experimentation could responsibly resume or the project could move toward real-capital execution.

## 2. Completion boundary

### Completed

Execution Readiness through `EXECUTION_READY` is implemented, adversarially reviewed, frozen, pushed, and independently remote-backed. Its final governing source commit is `7ba0bcc443e5efb7b7945c209c4f7fce46a06898`.

`READINESS_VALIDATED` and `EXECUTION_READY` are distinct:

- `READINESS_VALIDATED` establishes that a canonical readiness candidate passed the frozen Slice-4 authority reconstruction. It does not imply publication, sealing, currentness, or launch authority.
- `EXECUTION_READY` establishes that the published and sealed readiness authority is current under the frozen current-readiness contract. It permits the later launch-validation lifecycle to begin. It does not mean an experiment has launched, execution is authorized, or capital may be deployed.

### Deferred

The miner itself is not complete. Launch validation and every later execution lifecycle remain outside this boundary. Completing the source implementation did not create a real experiment-specific evidence-publication commit `E` or readiness seal `R`, and this checkpoint does not authorize real-capital deployment.

## 3. Governing authority chain

The following tracked authorities were byte-verified at this checkpoint's governing source commit:

| Authority | Tracked source | SHA-256 |
|---|---|---|
| Phase-3C intermediate checkpoint | [checkpoint](ore-v3-execution-readiness-phase3c-intermediate.md) | `5800b9daf5a9625672966e24ee8f42240cea6e72685e6292285d602fa6e9cff9` |
| Execution Readiness v1.1 | [specification](../research/specifications/experiment-execution-readiness-v1.1.md) | `e938499cc254ce2d65fce925fb6e33c5d8b9dcea73a91a2c01e1017e8fb17da9` |
| Clarification governance | [decision](../research/governance/execution-readiness-v1-clarification-decision.md) | `ce9e7cd57df0d31db5aea0c7674edc3b3b717b96a790d5c7e3075364df151477` |
| Readiness-test-policy-v2 governance | [decision](../research/governance/execution-readiness-v1.1-readiness-test-policy-versioning.md) | `e0d79b517b126633bb2f39448c61a84307dfd3b51628a39c8501eb7653fe20fd` |
| Prerequisite-authority governance | [decision](../research/governance/execution-readiness-v1.1-prerequisite-authority-identities.md) | `50c5bfbfa419ffe723665bbe9e853f98ec301e47a13f6ec55adcf03d9d01f88c` |
| Readiness-record-v2 governance | [decision](../research/governance/execution-readiness-v1.1-readiness-record-v2.md) | `debe9e0f91e3f420ad673ced84890071f0123cfe8ab159d20a08973c09817cb3` |
| Zero-input Phase-3B governance | [decision](../research/governance/execution-readiness-v1.1-zero-input-phase3b-evidence.md) | `1c70699297837ab18f1081075626f2fa4d2d586607f2dd3a25d930ea212538ef` |
| Detached Phase-3B evidence-publication governance | [decision](../research/governance/execution-readiness-v1.1-detached-evidence-publication.md) | `7b91d9f63ebfe0dfc72bdc1dfe2fdb687e6f1f60877537206d649cc8d00bd077` |

Frozen historical documents retain their exact bytes. A newer document must not silently replace or reinterpret their authority.

## 4. Frozen milestone history

The important verified milestones are:

| Milestone | Commit |
|---|---|
| Phase-3B handoff historical checkpoint | `4bfd568bbeabc58aa400b2b7c3ad4d0e12be4434` |
| Execution Readiness v1.1 clarification/specification governance | `f7e09f0e2c24f17dedca879c817ae3c78cda7026` |
| Phase-3C Slice 1 | `d1580d5aca721eca6a79129ceac04926a1daabd4` |
| Readiness-test-policy-v2 governance | `ace3d3257d2579d839c47f06f2650da36215496c` |
| Phase-3C intermediate checkpoint | `236dbee9e2909cb743d038efb2e7186fe574ba90` |
| Slice-2 prerequisite-authority governance | `4dde0200765f4b42209919d74dc84b8f383a7a67` |
| Phase-3C Slice 2 | `5a25b877ba57a50095e13da1372d036b4e908fdd` |
| Slice-3 readiness-record-v2 governance | `9184e2caefc2615e836cd17ece912159880cb73a` |
| Phase-3C Slice 3 | `f7691f0c243c6cb1f68c0253fcfdc568d3651ee1` |
| Zero-input Phase-3B evidence governance | `02c83f39d0dd4fe9af1843c01d9621519bac72e6` |
| Phase-3C Slice 4 | `8defc9afe7921e8175bbc352409ea23f276fd513` |
| Detached-evidence-publication governance | `80d8bc531d224ccb2c53eab70f009a9e89b2584f` |
| Phase-3C Slice 5 | `7ba0bcc443e5efb7b7945c209c4f7fce46a06898` |

These entries distinguish historical checkpoints, frozen specifications and governance decisions, implementation slices, and the final governing source commit. Future continuation begins from this comprehensive checkpoint once frozen and from `7ba0bcc443e5efb7b7945c209c4f7fce46a06898`; it does not restart from the Phase-3B handoff.

## 5. Completed authority architecture

The completed flow is:

```text
frozen source authority S
  + explicitly selected historical/prospective schema registry
  + committed prerequisite, adapter, profile, runtime, and configuration authority
  → prospective detached Phase-3B evidence preparation
  → evidence-preparation-v2 aggregate and subordinate evidence identities
  → readiness-record-v2
  → one readiness_identity
  → Slice-4 independent candidate evaluation
  → READINESS_VALIDATED or canonical READINESS_REJECTED

READINESS_VALIDATED
  → publication of the already-validated detached evidence graph
  → Git evidence-publication commit E
  → separate canonical readiness-record publication
  → Git readiness seal R
  → freshly fetched approved remote head H
  → current-readiness reconstruction and current-input verification
  → EXECUTION_READY or canonical CURRENT_READINESS rejection
```

`CANONICAL_RECEIPT_UNAVAILABLE` remains a narrow payload-free control result when receipt-capable evaluation has not been entered or canonical receipt construction itself is impossible.

### S, E, R, and H

- `S` is the frozen source commit bound by the readiness candidate.
- `E` is the prospective detached Phase-3B evidence-publication Git commit. It publishes already-validated canonical evidence metadata only. It is not a lifecycle state, semantic evidence identity, readiness identity, seal, attempt, launch object, or control record.
- `R` is the readiness seal Git commit. It is single-parent and changes only the canonical readiness-record path to the exact canonical record bytes.
- `H` is the freshly fetched approved remote head pinned for one coherent current-readiness resolution.

The sole canonical readiness-record path is:

```text
docs/research/readiness/<experiment-identifier>.json
```

`<experiment-identifier>` is the normalized governed experiment identifier. Alternate paths carry no readiness authority. `R` changes exactly this canonical readiness-record path and no other path. This path is distinct from the detached-evidence root, whose governed placeholder convention remains `docs/research/readiness/evidence-v1/<experiment_identifier>/<evidence_preparation_identity>/`.

The required approved first-parent authority relationship is:

```text
S first-parent-ancestor-of E
E first-parent-ancestor-of R
R first-parent-ancestor-of-or-equal-to H
```

`E`, `R`, and `H` do not feed backward into Phase-3B evidence identities, the evidence-preparation identity, or the readiness identity. The authority graph is acyclic.

## 6. Readiness-record-v2 and registry authority

The prospective readiness record has exactly one `readiness_identity` and governed closed 18-section material beneath it. Its identity domain is:

```text
orev3:experiment-execution-readiness:v1\n
```

The identity material excludes `readiness_identity` itself. There is no second aggregate readiness identity. The record remains outcome-value-free and does not itself persist lifecycle state.

Fresh prospective v1.1 authority selects these materially relevant revisions:

- readiness-record v2;
- adapter-declaration v3;
- profile-conformance-evidence v2;
- readiness-test-policy v2;
- Replay evidence v2;
- population-accounting evidence v2;
- evidence-preparation v2.

Historical revisions remain immutable and are explicitly selected for historical reconstruction. Registry progression is exactly:

```text
Historical:  6 → 10 → 20
Prospective: 6 → 10 → 20 → 29
```

Same-kind version substitution does not increase the semantic-kind count. Selection has no ambient `latest`, filesystem discovery, fallback, dual-revision membership, or 30th semantic kind.

## 7. Slice-2 prerequisite authority

Slice 2 froze prerequisite declarations for:

- allocation authority;
- allocator client and allocator contract;
- control-storage component and reusable control-storage contract;
- attempt-output declaration;
- output policy and revision;
- namespace identity policy;
- collision policy;
- supported attempt kinds;
- attempt identity domain and schema authority.

These are prerequisite authority declarations only. Execution Readiness does not allocate, consume an ordinal, realize a namespace, contact live control storage, create an attempt, or create a control record.

## 8. Adapter-v3 and external-input authority

Fresh prospective v1.1 authority explicitly selects adapter v3. It supports a governed regular-file branch and ordered-file-collection branch. Ordered collections bind exact member cardinality and semantic order through their manifest and declaration authority rather than filesystem enumeration order. Authority also binds parser configuration, governed decoder authority, source commit, and committed component reconstruction.

Historical adapter v1 and frozen Slice-2 adapter v2 remain historically preserved. The production adapter registry remains empty and therefore fail-closed; no placeholder production adapter is authorized.

## 9. Frozen zero-input authority

The prospective zero-input model is exact:

- external-input declarations and snapshot, dataset, and projection evidence collections are empty;
- projection authority is derived under `orev3:experiment-zero-input-projection-authority:v1\n` rather than represented by synthetic projection evidence;
- candidate order is `[]`;
- ordered scientific source, Replay-unit, and decision vectors are empty;
- population source, included, and excluded counts are zero, and dispositions are empty;
- no synthetic source unit, sentinel disposition, snapshot, dataset, projection evidence, parser worker, projector worker, dataset-validator worker, or Replay-preparation worker is fabricated;
- the semantic-component vector contains the four governed Replay preparer, observation selector, profile validator, and artifact validator component identities;
- the worker vector contains exactly the normalized prospective Phase-3A validator, readiness collection `collection-a`, readiness collection `collection-b`, and readiness execution `execution` identities;
- prospective Phase-3A authority is normalized and excludes operational dependency-root and temporary paths.

Zero-input invariants remain applicable and must pass; they are not converted to `not_applicable`.

## 10. Detached Phase-3B evidence publication

The canonical prospective graph root is:

```text
docs/research/readiness/evidence-v1/<experiment_identifier>/<evidence_preparation_identity>/
```

It contains:

```text
aggregate.json
objects/<semantic-kind>/<object-identity>.json
workers/<worker-evidence-identity>.json
```

The exact evidence-object namespace tokens are:

1. `immutable-input-snapshot`
2. `dataset-validation-evidence`
3. `outcome-blind-projection-evidence`
4. `replay-evidence`
5. `population-accounting-evidence`
6. `readiness-test-evidence`
7. `profile-conformance-evidence`
8. `artifact-declaration-evidence`

The canonical evidence-preparation-v2 aggregate is the sole graph root and manifest; no second graph identity exists. Published objects and closed worker transport bundles use canonical UTF-8 JSON with sorted keys, no insignificant whitespace, and exactly one final LF. Git entries are regular `100644` blobs. Expected closure derives from the aggregate and worker vector, while tree enumeration is only a closure check. Aliases, alternate extensions, symlinks, submodules, missing objects, extra files, and path/embedded-identity disagreement fail closed.

The graph contains canonical evidence metadata and governed worker authority only. It excludes raw scientific payloads, raw current-input contents, outcomes, credentials, secrets, operational paths, caches, dependency environments, and uncontrolled logs.

`E` may occur only after `READINESS_VALIDATED`. It is single-parent and performs one atomic absent-to-complete publication of exactly one selected graph root, with no readiness-record or unrelated path change. It must be pushed, reachable, and remote-backed before `R` can qualify. An identical already-published graph reuses its original qualifying `E`; no no-op publication commit is created. Divergent or partial preexistence is a collision. Any selected-root mutation, removal, or removal and reintroduction after `E` is ambiguous.

## 11. Slice-4 candidate result model

Slice 4 has exactly three terminal result forms:

1. `READINESS_VALIDATED`
   - carries the exact canonical readiness-record-v2 candidate bytes, reconstructed readiness identity, and validated record authority;
   - implies no persistence, `E`, or `R`.
2. `READINESS_REJECTED`
   - carries a canonical readiness-failure-receipt-v1;
   - records the first governed failure in the exact 27-entry invariant vector;
   - performs no scientific execution.
3. `CANONICAL_RECEIPT_UNAVAILABLE`
   - is payload-free and identity-free;
   - is restricted to the narrow pre-entry or internal receipt-construction boundary.

Slice 4 itself does not publish `E` or `R`.

## 12. Current-readiness resolution

Current readiness performs one authoritative approved-ref fetch and pins one coherent `H`. From fetched Git history and objects it resolves the canonical readiness record, derives `R`, derives the selected evidence graph and qualifying `E`, validates exact graph closure and canonical bytes, independently reconstructs complete first-order Phase-3B evidence, reconstructs governed authority at `S`, detects governed source drift, and verifies current external-input availability and exact bytes.

It does not use working-tree or local-only authority, perform a second uncontrolled fetch, rerun scientific Replay, parse outcomes, contact live control storage, or create a launch snapshot.

The exact current-readiness invariant order is:

1. `git_authority`
2. `canonical_readiness_record`
3. `schema_registry`
4. `experiment`
5. `readiness_specification`
6. `control_plane`
7. `source_scopes`
8. `protocol`
9. `implementation`
10. `execution_specification`
11. `execution_profile`
12. `runtime`
13. `configuration`
14. `external_inputs`
15. `replay`
16. `artifacts`
17. `outcome_policy`
18. `validation`
19. `attempt_policy`
20. `readiness_seal_and_ancestry`
21. `current_external_inputs`

The first governed failure owns the result. Fully downstream-rehashed evidence substitution remains subject to independent first-order reconstruction at its actual owner.

## 13. CURRENT_READINESS failures

The exact non-ready dispositions are:

- `READINESS_UNRESOLVED_REMOTE`
- `READINESS_AMBIGUOUS`
- `READINESS_INVALID_RECORD`
- `READINESS_ORPHANED`
- `SUPERSEDED`
- `READINESS_STALE`
- `READINESS_INPUT_MISMATCH`
- `READINESS_BLOCKED_INPUT_UNAVAILABLE`

The deterministic current-readiness failure mapping is:

| Condition | Disposition | Failed invariant |
|---|---|---|
| Approved remote cannot be freshly resolved or fetched | `READINESS_UNRESOLVED_REMOTE` | `git_authority` |
| Required evidence object is invalid, missing, noncanonical, or false | `READINESS_INVALID_RECORD` | Earliest governed semantic owner: snapshot/dataset/projection → `external_inputs`; Replay/population → `replay`; artifact evidence → `artifacts`; profile evidence → `outcome_policy`; readiness evidence or worker authority → `validation` |
| Aggregate or graph closure is invalid, missing, noncanonical, extra, or false | `READINESS_INVALID_RECORD` | `validation` |
| Graph bytes are valid but no qualifying `E` precedes `R` | `READINESS_ORPHANED` | `readiness_seal_and_ancestry` |
| Multiple qualifying/root transitions exist, or the selected graph is mutated, removed, or removed and reintroduced after `E` | `READINESS_AMBIGUOUS` | `readiness_seal_and_ancestry` |
| An older readiness seal is displaced by the current qualifying seal | `SUPERSEDED` | `readiness_seal_and_ancestry` |
| Governed committed source authority has drifted | `READINESS_STALE` | Earliest governed semantic owner |
| Current external-input bytes, digest, cardinality, or semantic order differ | `READINESS_INPUT_MISMATCH` | `current_external_inputs` |
| A required current external input is unavailable | `READINESS_BLOCKED_INPUT_UNAVAILABLE` | `current_external_inputs` |

Remote transport authority belongs to `git_authority`; canonical candidate corruption belongs to `canonical_readiness_record`; and `E` shape, reachability, uniqueness, and history belong to `readiness_seal_and_ancestry`. An `E` mutation is ambiguity, not ordinary source staleness. No condition introduces a ninth disposition.

Rejections use readiness-failure-receipt-v1 with receipt class `CURRENT_READINESS`. All 27 invariant entries are serialized in frozen order. Invariants 1–21 are applicable; 22–27 are `not_applicable`. Exactly one applicable invariant is failed, earlier applicable invariants are passed, and later applicable invariants are not evaluated. Receipts contextually bind experiment, repository, and approved ref; source and readiness identities follow actual known/absent progression; launch snapshot identity is always absent. Successful current readiness creates no receipt.

`CANONICAL_RECEIPT_UNAVAILABLE` is not an ordinary current-readiness failure escape hatch. When canonical receipt construction is available, Git, graph, evidence, seal, drift, and current-input failures produce canonical `CURRENT_READINESS` receipts.

## 14. Meaning of EXECUTION_READY

`EXECUTION_READY` means the sealed readiness authority is current under the frozen current-readiness contract. Among other requirements, it needs a qualifying pushed `E`, qualifying pushed `R`, fresh coherent `H`, valid canonical readiness record, complete independently reconstructed detached evidence, current governed source authority, and exact current external inputs.

`EXECUTION_READY` does **not** mean:

- a launch-authority snapshot exists;
- immutable launch-input snapshots exist;
- launch validation or smoke passed;
- live control storage or an allocator is available;
- an output namespace is realizable;
- an allocation, ordinal, attempt identity, or control record exists;
- an experiment has launched or scientific execution has begun;
- capital may be deployed.

It authorizes only the later launch-validation lifecycle to begin.

## 15. Information-flow and lifecycle boundaries

Execution Readiness through `EXECUTION_READY` remains outcome-free. It does not consume outcome values, labels, winners, scientific result interpretations, strategy-visible outcomes, outcome-bearing `DecisionContext` or `FeatureContext`, future-outcome rankings, evaluation callbacks, or scientific execution. Outcome-aware profiles bind authorization authority only; readiness does not open or interpret outcomes.

Authorized within the completed architecture:

- read-only committed-authority reconstruction;
- prospective evidence preparation;
- canonical candidate construction;
- canonical rejection receipts;
- governed `E` publication after successful validation;
- reviewed `R` publication as a separate operational/governance action;
- one fresh Git fetch for current readiness;
- current external-input byte, digest, cardinality, order, and availability checks.

Not yet authorized or implemented as the next lifecycle:

- launch-authority snapshot;
- immutable launch-input snapshots;
- launch smoke;
- a second launch fetch;
- live control-storage availability or writability checks;
- output-namespace preflight or realization;
- allocation or ordinal consumption;
- attempt identity or `STARTED` control record;
- terminal control lifecycle or recovery;
- outcome opening or authorization creation;
- ranking or evaluation;
- experiment execution;
- real-capital mining.

## 16. Final validation evidence

The material final regression and review evidence is:

- Slice 3 complete execution suite: 520 tests passed.
- Slice 4 complete execution suite: 590 tests passed.
- Slice 5 complete execution suite: `621 passed in 5692.20s`.
- Final Slice-5 targeted adversarial re-review: BLOCKER 0, HIGH 0, interoperability-blocking MEDIUM 0.
- The fully downstream-rehashed Replay-evidence attack rejected at `replay`.
- The population-accounting-evidence attack rejected at `replay`.
- The evidence-preparation aggregate attack rejected at `validation`.
- Zero-input, regular-file, ordered multi-member, and outcome-aware authority-only current-readiness paths reached `EXECUTION_READY`.
- Detached evidence graph publication and retrieval were adversarially validated.
- `E` uniqueness, ancestry, idempotency, collision, mutation, removal/reintroduction, orphan, and ambiguity behavior were validated.
- Contextual `CURRENT_READINESS` receipt behavior was validated.
- The production adapter registry remained empty and fail-closed.
- Historical Phase-2/3A/3B and frozen Slices 1–4 remained preserved.

Some detached-worker tests can fail inside the nested macOS Seatbelt sandbox with exit 71 and pass under the established authorized external execution workflow. Those are infrastructure failures, not repository defects. Full suites were not rerun after every targeted review: where the exact implementation fingerprint was unchanged, already-bound test evidence was reused explicitly for those exact bytes.

## 17. Final Slice-5 implementation identity

The exact reviewed and frozen Slice-5 fingerprint is:

```text
f733e5b47ea96bba9f38ef3553030ca72effb421dec091358deef2105211b28f
```

The frozen Slice-5 commit is `7ba0bcc443e5efb7b7945c209c4f7fce46a06898`; its parent is `80d8bc531d224ccb2c53eab70f009a9e89b2584f`.

The exact reviewed eight-path set committed by Slice 5 is:

```text
src/orev3/execution/current_readiness.py
src/orev3/execution/detached_evidence.py
src/orev3/execution/git_state.py
src/orev3/execution/readiness_candidate.py
src/orev3/execution/readiness_record.py
tests/execution/test_phase3c_current_readiness.py
tests/execution/test_phase3c_readiness_contracts.py
tests/execution/test_phase3c_readiness_record_v2.py
```

The commit was pushed normally without force. Local, tracking, and independently queried remote heads matched it with ahead/behind `0/0`. No real `E` or `R` was created while freezing the source implementation.

## 18. Production fail-closed and repository security

The production adapter registry remains empty. No placeholder production adapter is authorized, so the source implementation cannot accidentally establish production `EXECUTION_READY` for a real experiment without genuine registered authority. No real allocator, backend, control-storage, outcome, or execution route was introduced merely to complete Execution Readiness. This is an intentional safety property, not missing test scaffolding.

Do not store or commit personal data, passwords, API keys, private keys, wallet seed phrases, secrets, tokens, credentials, or confidential information. Use environment variables and untracked local configuration for secrets. Raw research and runtime data remain outside Git unless specifically governed as safe canonical metadata. The detached evidence graph is metadata-only and excludes raw scientific payloads, outcomes, credentials, secrets, operational paths, caches, dependency environments, and uncontrolled logs.

## 19. Repository state and inherited work

At the final Slice-5 freeze, the index was empty, branch/tracking/remote were synchronized, and the frozen Slice-5 implementation was clean and committed. Unrelated inherited backlog and research work deliberately remained uncommitted. Its preserved fingerprint was:

```text
01d0f934e07f2c4955752fcd1603274c989a6abf1168501b5e21184dc53ec001
```

That inherited work is not Execution Readiness authority and must not be staged or committed with this checkpoint.

## 20. Continuation guardrail for a fresh ChatGPT/Codex session

In a fresh ordinary ChatGPT chat, the assistant may not have direct filesystem access to the user's local `orev3` checkout. The default continuation workflow must not ask the user to upload or attach the repository or checkpoint.

Instead:

1. Use this remembered checkpoint only as orientation.
2. Instruct Codex, which has repository access, to inspect and verify this tracked comprehensive checkpoint from synchronized branch `research/post-v1`.
3. Verify the checkpoint's committed SHA-256 and governing source commit `7ba0bcc443e5efb7b7945c209c4f7fce46a06898`.
4. Verify local, tracking, and independently queried remote heads, ahead/behind, index state, and inherited-work preservation.
5. Have Codex report the verified checkpoint and repository state before authorizing new implementation.

The tracked checkpoint is the detailed source of truth. Do not rely on conversational memory alone when repository verification is available.

## 21. Next decision boundary

After this checkpoint is targeted-review approved, frozen, pushed, and independently remote-backed, the immediate next activity is:

```text
READ-ONLY POST-EXECUTION-READINESS NEXT-MILESTONE INVESTIGATION
```

unless an already-frozen tracked authority establishes a narrower next step.

That bounded investigation must choose the smallest coherent milestone toward a trusted real-SOL miner. Possible later areas include experiment-specific candidate and evidence publication, reviewed seal `R`, launch-authority and immutable input snapshots, launch validation, smoke, a second fetch, live control-storage checks, namespace preflight, allocation, ordinal consumption, attempt/control lifecycle, recovery, outcome authorization, ranking/evaluation, scientific execution, and paper/live-miner integration. This checkpoint does not authorize those areas together and does not declare a new implementation slice.

## 22. Supersession rule

Once this checkpoint itself is reviewed, frozen, committed, pushed, and independently remote-backed, future ordinary continuation starts here and at governing commit `7ba0bcc443e5efb7b7945c209c4f7fce46a06898`. The Phase-3B handoff and Phase-3C intermediate checkpoint remain historical evidence of their milestone state and authority. They are not deleted, rewritten, replaced as historical authority, or used as the default point from which to restart current work.
