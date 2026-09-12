# ORE V3 — Durable Execution and Continuation Protocol

**CANDIDATE — NOT ADOPTED — NOT CONTROLLING — INDEPENDENT REVIEW REQUIRED.**

Created 2026-09-12 for prospective project-wide workflow. Creation and self-audit authorize no implementation, correction, operational activity, staging, commit or push. This document takes effect only after exact-byte authentication, independent review, explicit adoption for continuation, and any stronger applicable Git-effectiveness requirements. Review alone does not activate it. Its final identity is recorded externally; it contains no self-referential hash.

The objective is a trustworthy ORE miner eventually capable of operating with real SOL. Shorter prompts and selective evidence retrieval serve that objective without reducing the trust standard.

## 1. Precedence and inherited authority

This protocol is subordinate to stronger adopted specifications, governance, protected contracts, and explicit continuation constraints. It governs workflow, not cancellation, recovery, financial, scientific or readiness semantics. A task-specific restriction overrides generic convenience. A task cannot use this protocol to silently amend stronger governance. An actual conflict requires diagnosis and the separately authorized governance decision before dependent work.

Authenticate adoption bindings rather than infer status from a filename, historical candidate banner, or presence in Git. Distinguish committed remote-backed authority, reviewed but uncommitted evidence, intentionally preserved mutable work, and proposals. None substitutes for another. Frozen specifications and historical evidence retain their original meanings and identities; a prospective procedure cannot relabel a historical failure or make an experiment repository-qualified.

The controlling checkpoint at creation is [the Stage-3C comprehensive continuation checkpoint](../../project-checkpoints/ore-v3-stage3c-cancellation-capability-architecture-pre-implementation-comprehensive-continuation.md), 251990 bytes, 1740 lines, SHA-256 `143010a4f5d24242ec10c0e2793925f5939d932822f5aa3aa29fb20e82de727d`. Its independent review is PASS. Its Appendix B supplies exact adopted bindings for these nine documents; their stronger requirements remain intact:

1. [Bounded streaming source-processing prerequisite](rq003-experiment-005-bounded-streaming-source-processing-prerequisite-v1.md).
2. [Acquisition lifetime](rq003-stage3c-acquisition-lifetime-clarification-candidate.md).
3. [Admission serialization](rq003-stage3c-admission-serialization-clarification-candidate.md).
4. [Category attribution](rq003-stage3c-category-attribution-clarification-candidate.md).
5. [Controller retirement status](rq003-stage3c-controller-retirement-status-clarification-candidate.md).
6. [Recovery permission](rq003-stage3c-recovery-permission-clarification-candidate.md).
7. [Worker pinned-input acquisition lifetime](rq003-stage3c-worker-pinned-input-acquisition-lifetime-clarification-candidate.md).
8. [Sole-reaper interruption/admission](rq003-stage3c-sole-reaper-interruption-admission-clarification-candidate.md).
9. [Sole-reaper receipt/settlement](rq003-stage3c-sole-reaper-cancellation-receipt-settlement-clarification-candidate.md).

The existing [Execution Readiness v1.1 specification](../specifications/experiment-execution-readiness-v1.1.md) and its applicable clarification, test-policy versioning, prerequisite-identity, readiness-record, zero-input and detached-publication decisions retain their exact revision selection, validation, isolation, publication and immutable-history requirements. This protocol does not replace readiness evidence or its governed tests with workflow manifests. Relevant scientific authority, `AGENTS.md`, and [SECURITY.md](../../../SECURITY.md) also remain controlling in their domains. Features may not use future/outcome information; secret material must not enter source, evidence, logs or Git.

The authenticated broader architecture is `/private/tmp/orev3-production-architecture-q9vhi2qj`, manifest 1119 bytes, SHA-256 `bedf816f7bcb1856ccc49271b9d4373a88b46be00ddb5ace8153c56f772cfcf9`; its complete report is also checkpoint Appendix E. In particular, §K requires separate authorization and independent review for each increment and says: “A failed increment is diagnosed, not automatically repaired under the same permission.” Sections 3, 6 and 7 below do not waive those requirements.

## 2. Default continuation: checkpoint plus authenticated delta

A continuation task identifies a reviewed comprehensive checkpoint and a bounded, authenticated delta from it. Conversational memory is non-authoritative for project-critical facts. A summary can locate evidence; it cannot authenticate it or grant permission.

Before writes or experiments, authenticate:

- The protocol's exact path, byte identity and adoption/effectiveness record, and the checkpoint's exact identity and review record.
- Repository path, branch/upstream, local HEAD, tracking HEAD, independently queried live-remote branch HEAD, ahead/behind, index, and full mutable path inventory with tracked/untracked classifications.
- Current delta authority and relevant source/test/evidence identities, including their relationship to the checkpoint and any prior failure/review.
- Protected/frozen identities the delta could affect, including indirect dependencies. Establish the preservation baseline required by stronger authority before writes.

Use `GIT_OPTIONAL_LOCKS=0` or `git --no-optional-locks`. Query the live remote without fetching or changing refs; a tracking ref is not an independent remote observation. An unavailable remote is unresolved authentication, not proof of equality. Run `git diff --check`; check new untracked text separately because Git's ordinary diff omits it. Never refresh the index, stage, clean, reset, or touch live operational storage merely to simplify authentication.

Read the complete authority and current evidence materially needed for the task. Do not automatically reauthenticate every historical external artifact on every small increment when the reviewed checkpoint authenticates that history, the task does not depend on reopening it, and no mismatch exists. Record which history was referenced through the checkpoint and which primary artifacts were checked now. Never report an unperformed recheck as performed.

This is a default retrieval optimization, not a waiver of full preservation or a stronger inventory requirement. The current Stage-3C checkpoint's §10 requires its 698-path inventory and specified bindings; that requirement remains. A task expressly requiring all bound external identities still requires them. Changing such a requirement needs its own compatible authority; adopting this generic protocol does not silently supersede it.

Reopen deeper primary history when there is a protocol/checkpoint mismatch, unexplained delta, missing required artifact, governance ambiguity, protected-identity mismatch, result contradicting checkpointed evidence, proposed qualification crossing, or an insufficient checkpoint-to-delta chain. Expand authentication to the affected dependency/authority closure; stop on unexplained mismatch. Do not reconstruct missing proof from memory, substitute a similarly named artifact, or repair an evidence package.

After work, independently reconcile the exact authorized delta against the baseline. All non-authorized paths, modes, identities and classifications remain unchanged. Recheck Git/index/live remote and mutable counts. Unexpected concurrent changes are a stop condition, not cleanup permission.

## 3. Risk classification and workflow

Classify the actual effects and failure boundaries before work. The highest applicable class governs a mixed task. LOW is not an exemption from stronger review or validation rules. Escalation is permitted and recorded; silent downgrade is prohibited. If the applicable risk class is uncertain, the task MUST NOT proceed at the lower plausible class: it MUST either use the highest plausible risk class until sufficient evidence resolves the uncertainty, or STOP pending sufficient evidence to classify it safely. Uncertainty itself triggers this requirement; HIGH-risk effects need not already be proven. Lack of evidence is not evidence of lower risk. Reclassification to a lower class is permitted only after sufficient evidence resolves the uncertainty, subject to the explicit decision required below. Inconvenience or cost never permits proceeding at a lower class while uncertainty remains. A downward reclassification needs an explicit, evidence-supported decision compatible with stronger authority before using reduced procedures.

| Class | Examples | Default sequence, subject to stronger requirements |
|---|---|---|
| LOW | Inert definitions, types/state views, documentation, mechanical bindings, side-effect-free tests | Authenticate delta → implement within exact scope → targeted checks/tests → compact semantic/scope review → freeze evidence |
| MEDIUM | Lifecycle/state transitions, ownership/private registry, deterministic local failure handling, non-live executors | Authenticate delta → pre-record adverse boundaries → implement → targeted and adverse validation → independent semantic review → freeze evidence |
| HIGH | Actual signals, source ownership/cut, callback ingress, uncertain external action, processes/children, shutdown/restoration, production execution, real-SOL capability | Authenticate full relevant authority → pre-record semantic oracles/adverse schedules → narrow implementation → targeted/adversarial validation → independent adversarial review → explicit qualification reconciliation → required major evidence/checkpoint treatment |

A documentation change that alters safety authority is not made LOW by its file extension. Every workflow is limited by task authorization; implementation permission does not itself authorize a later independent review, checkpoint, experiment, staging, commit or push. If those steps require separate authorization, freeze the current evidence and report the next prerequisite.

## 4. Adversarial validation before success claims

For MEDIUM/HIGH work, derive and record applicable adverse boundaries and expected semantic outcomes before execution, and before implementation where practical. Explain any boundary that cannot yet be specified; resolve material authority ambiguity before coding around it. Oracles come from adopted authority, never from the desired result. Required schedules must be authorized before execution.

Consider interruption immediately before and after each success/commit linearization point; failure with apparently clean prerequisites; repeated eligible events; reentry/competing owners; stale retained state; terminal-state boundaries; uncertain-before and uncertain-after action; and source-open versus source-closed histories. Record both expected state/evidence and prohibited outcomes. Keep historical prerequisites distinct from committed terminal authority.

Instrument distinctions rather than infer them: generation, runtime pending if measured, callback ingress, qualified receipt, membership, action claim, entry, completion, native closure, invocation terminality, source cut, restoration and caller result. Unmeasured pending state stays unmeasured. Callback occurrence is not receipt or delivery; retained obligation is not completed delivery; FAILED is not CLOSED; non-executable is not PASS.

Independent review remains free to identify missing schedules and run additional probes within its authorization. A passing implementation suite never restricts review. Count executions once, even when one history supports several gates; do not count static analysis/authentication as runtime tests. Distinguish synthetic prerequisites from operational producers and experimentally qualified behavior from repository/runtime qualification.

## 5. Stop and evidence discipline

Stop dependent work at a semantic defect, invalid instrumentation, authority ambiguity, preservation mismatch, scope expansion or unmet prerequisite, except for a correction expressly eligible under §6. Preserve the first decisive negative and its original oracle, candidate identity, trace, caller result, state/evidence and qualification consequence. Do not rescue an experiment to obtain a preferred verdict. Invalid instrumentation is not semantic PASS or FAIL; absent evidence is not proof of correctness.

Do not silently broaden paths, weaken a validator/oracle, alter protected components, add production effects or reset failure authority. Report what is established, unresolved and unexecuted. Follow task-specific stop-at-diagnosis rules even when a likely correction is obvious.

## 6. Optional bounded one-correction envelope

Future MEDIUM/HIGH implementation tasks may explicitly include an optional envelope of at most ONE narrow correction after failed validation. The default when no compatible envelope is authorized is diagnosis and stop. This protocol is not automatic correction authority and does not override a stronger no-repair rule, including current architecture §K. Resolving a conflict with that rule requires separate explicit authority, not an implementation agent's convenience interpretation.

All conditions must hold before using the envelope:

- The defect and correction are wholly within already-authorized paths; no new repository path or protected/frozen modification is required.
- Adopted architecture/governance unambiguously determines the correction; no architectural redesign or governance interpretation/decision is needed.
- No qualification boundary, operational capability or financial authority expands; no test or semantic oracle is weakened.
- Original failing bytes/evidence are preserved; the one correction has a separate exact diff and identity.
- The decisive failing schedule runs FIRST against corrected bytes, followed by all required regressions and risk-appropriate independent review.

Record an eligibility checklist before correction. One attempt is a maximum, not a requirement. Stop if any condition fails, if the correction fails, or if another semantic correction would be needed. Do not split a broader repair into nominally separate edits to evade the limit. A new task does not erase the previous failure/correction count; further correction needs fresh explicit scope and authority. This envelope concerns development changes, not retries of external actions, recovery of governed terminal records, or replay of uncertain actions.

A review-only or diagnosis-only task never acquires repair permission from this section. The current I2 correction remains unimplemented and separately authorized work; its future independent re-review is mandatory.

## 7. Review policy

LOW may use compact same-task or independent review only where stronger governance permits. MEDIUM requires independent semantic review before crossing the increment's qualification boundary. HIGH requires independent adversarial review. Identify reviewer independence, exact reviewed identities, authority mapping, adverse coverage, scope/preservation, findings and qualification limits.

Independent review is required whenever a prior independent review found a semantic defect, real signals/processes/external effects are involved, source ownership/cut/restoration or uncertain action is involved, production qualification is claimed, or real-SOL capability is approached. Existing per-increment independent review requirements remain even for an inert increment. Self-audit cannot substitute for them.

Review may reuse authenticated primary evidence when rerun adds no semantic value. It must inspect sufficient primary bytes/traces and oracle timing to support conclusions, not inherit PASS labels or test names. A failed review blocks progression until authorized correction, required validation and separately authorized re-review close the finding.

## 8. Compact evidence policy

Each implementation/review task retains authority references, exact baseline-to-task delta, file identities, commands/probes and exit statuses/counts/warnings, results, stop/correction history, preservation checks and precise qualification claims. Record unexecuted requirements and blockers. A compact manifest contains relative artifact path, byte size and SHA-256; bind external dependencies separately by exact path/identity and role. Protect secrets under SECURITY.md.

Reference authenticated checkpointed history instead of copying giant packages without need. Preserve original negative controls and immutable evidence. Temporary storage is not a durability guarantee: before a required artifact disappears or a context/device migration, retain sufficient authenticated continuity evidence through separately authorized durable publication/checkpoint work. Missing primary proof remains missing. A manifest proves byte identity, not semantic sufficiency. Never include a purported self-hash fixed point in the object being hashed.

Freeze evidence after final validation/preservation. Later code or test edits invalidate the corresponding final identity and require appropriate revalidation under authorization. Keep committed, paused and new task diffs separate; never absorb unrelated mutable work into a passing implementation report.

## 9. Checkpoints and context risk

Do not create comprehensive checkpoints after every increment. Use smaller evidence artifacts between major boundaries. A new comprehensive continuation checkpoint is required at major Stage/slice completion, material architecture change, substantial independently qualified integration, approaching commit/push preparation, cumbersome accumulated delta, threatened context continuity, or migration that would otherwise depend on memory. Honor any stronger milestone-specific checkpoint timing.

Create a checkpoint before abandoning context when accumulated delta would otherwise be lost. This applies to ChatGPT replacement, Codex lane/project replacement and device/project migration. If checkpoint creation is not authorized in the current task, identify the continuity blocker and obtain separate authorization before proceeding into a context-dependent boundary; do not silently create an extra repository path. Preserve historical checkpoints rather than overwrite frozen authority. Independent checkpoint review is required when it becomes primary authority for substantial/HIGH-risk continuation.

Every new comprehensive checkpoint must contain a section titled **NEW CHAT / NEW CODEX LANE BOOTSTRAP** with:

- Repository location; protocol path, exact identity and adoption/effectiveness record; checkpoint path and externally recorded identity/review.
- Commands/methods to authenticate both and independently query local/tracking/live-remote authority without fetch, optional index refresh or ref changes.
- Exact mutable inventory/counts, baseline identities and accumulated authorized delta; committed versus mutable status.
- Protected/frozen paths and identities, required evidence locations, and deeper-authentication triggers.
- Current milestone, failures/limitations, next eligible work and its prerequisites, exact proposed scope, and still-prohibited work.
- Explicit authorization requirement, stop-on-mismatch instruction, and a warning that unavailable temporary evidence cannot be replaced by conversational memory.

The existing checkpoint is unchanged by this protocol; its historical next-step statements must be read with authenticated later delta, not silently edited or treated as current permission.

## 10. Compressed task header

After this protocol is effective, use the following header and reference it for unchanged general rules. Include enough delta evidence to reconstruct current authority; brevity must not conceal a blocker or qualification limit.

```text
CONTINUATION AUTHORITY

Protocol:
  <path>
  SHA-256: <identity>

Checkpoint:
  <path>
  SHA-256: <identity>

Current delta:
  <brief authenticated state and exact supporting evidence identities>

Risk class:
  LOW / MEDIUM / HIGH

Authorized paths:
  <exact paths and allowed operations>

Task:
  <exact objective and qualification boundary>

Required adverse boundaries:
  <task-specific list, or justified not applicable>

Stop conditions:
  <task-specific additions>

Correction envelope:
  <disabled, or explicitly authorized one-correction envelope compatible
   with stronger authority; identify its authority>
```

Task-specific authority overrides generic convenience. Stronger governance always overrides this protocol. A compressed header grants only its stated objective and paths, never all future work described in a checkpoint.

## 11. Staging, commit and push

Implementation != validation != review != staging != commit != push. None implies the next authorization.

Before commit, complete project-required tests/adversarial validation, independent review, exact preservation/diff accounting, evidence/governance consequences and comprehensive checkpoint/review where required. Authenticate the exact staging allowlist and staged bytes against reviewed identities; exclude unrelated dirty paths and secrets. Obtain explicit commit authorization. Authenticate the resulting parent, tree, paths and bytes. Push requires separate explicit authorization after commit authentication, followed by independent live-remote verification. Do not infer push authority from “cook,” a commit, or a PASS; establish the intended adoption unit and remaining prerequisites.

Existing governed evidence-publication and governance Git-effectiveness sequences remain unchanged. No forced push, fetch, ref change, blanket staging, readiness execution or production promotion follows from this protocol. Safe incremental commits remain possible only where adopted architecture permits an accurately labelled, independently qualified dormant unit; they cannot imply full Stage-3C completion.

## 12. Real-SOL and production boundary

Maximum/HIGH-risk treatment is mandatory for spending SOL, signing/broadcasting transactions, control of funded keys, autonomous capital allocation, attaching actors that can lead to spending, and changes to safety/execution boundaries protecting capital. Financial authority, amounts/scope and production qualification must be explicit and separately governed. No bounded correction may enlarge them. Never place keys, credentials or sensitive environment contents in evidence.

State vocabulary, synthetic completion prerequisites and experimental PASS are not production permission. Production source/capability shutdown/restoration, source activation, actor attachment and Gap 4D retain their unqualified boundaries until their own authorized work proves them. A non-executable limitation cannot become successful restoration evidence through documentation or reduced process.

## 13. Creation-time authenticated delta — historical anchor, not authorization

Repository `/Users/erale/Documents/orev3`; branch `research/post-v1`; upstream `origin/research/post-v1`. Local/tracking and independently queried live remote at drafting: `83b53e5294ad336e5b02fe0f941fb074d2d5756d`; ahead/behind 0/0; index empty. Pre-creation mutable boundary: 5 tracked modifications + 30 untracked = 35. This candidate adds one new untracked path; the expected post-creation count is 5 + 31 = 36, subject to independent final verification. These are dated baselines, not permanent counts for all future work.

I1 remains implemented, validated and independently reviewed PASS. I2 is implemented but its independent review is **B — I2 REVIEW FAIL — SEMANTIC / LIFECYCLE DEFECT**. All 72 baseline tests passed; an additional non-live precommit adverse probe exposed FAILED + SETTLED projection rejection. The valid I1 invariant is not a defect. Narrow correction design is **A — NARROW I2 LIFECYCLE / PROJECTION CORRECTION IS SUFFICIENT**. **Correction NOT implemented. I3 BLOCKED and NOT begun.** No current failure is closed by this protocol.

| Current evidence package | Manifest bytes | Manifest SHA-256 |
|---|---:|---|
| `/private/tmp/orev3-i2-review-o5xo6hkr` | 1445 | `9bc3d19e4dcd8f06fb6176adfc174959881d79c4d3992f3324b87a1926366343` |
| `/private/tmp/orev3-i2-projection-design-p3vb8go8` | 952 | `d412169510781d84f768660ea5c07ba1b265a610d74f2bc9c8c8a9d8732b5f5b` |

Both rows refer to `artifact_manifest.json`; manifests and all listed entries were authenticated for drafting. Current I2 source SHA-256 is `94474f2a5e9a563a54bcd06c3aeab1ca0e9afae70bf94ef40377f8fd26ee22e1` (14171 bytes); current test SHA-256 is `97cdf17aeaf9f9d1778c2f843735ed7e9bb91fab98f9cc1aa7566deefdcc5746` (21706 bytes). The checkpoint binds protected V7, frozen `_ControllerAcquisitionPolicy`, promoted blobs and paused runtime/test work; all remain unchanged.

Future I2 correction still requires explicit authorization, decisive adverse validation, applicable full I1/I2 regressions, and separately authorized independent re-review before I3 eligibility. Production COMPLETE, actual-SIGINT durability, source activation, production receipt/Gate-13 runtime behavior and shutdown/restoration remain unqualified by I2. Slice 4 remains paused. Stage 3C is not ready to cook/push or operate with real SOL.

## 14. Self-audit and activation gate

Drafting self-audit must compare authentication/preservation, experimental versus repository qualification, review independence, stop/correction rules, frozen boundaries, checkpoint continuity, commit/push separation and real-SOL restrictions against stronger authority. Correct only this new candidate during its authorized drafting task. Any unresolved material conflict blocks creation/adoption; do not call subordination a waiver.

This candidate's compact workflows do not supersede current full-inventory requirements, Stage-3C independent increment review, failed-increment diagnosis, primitive re-freeze, or adoption/Git-effectiveness duties. No historical evidence is reinterpreted. Exact-byte independent review and subsequent explicit adoption/effectiveness remain future work. **This protocol is NOT controlling.**
