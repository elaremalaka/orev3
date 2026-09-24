# ORE V3 CODEX LANE HANDOFF / AUTHOR-REVIEW PROTOCOL

Infrastructure status: **DRAFT-UNREVIEWED**. Semantic revision: `ore-v3-codex-lane-handoff/0.2.0`. Stable control-set revision: `CS01-CS25/1`. Independent HIGH-risk continuation-infrastructure review required. Created 2026-09-23. This workflow supplement is not yet an adopted replacement for any existing governance. Its present package frontier is RR-AR-PASS. Its present next operation is infrastructure review; architecture next gate after infrastructure PASS plus required adoption is focused CD author correction, subject to separately supplied authorization and applicable publication prerequisites.

## 1. Authority and task envelope

Build an ORE miner for the existing ORE cryptocurrency on Solana that can eventually be trusted to operate with real SOL. Workflow and checkpoints support that objective; they do not establish operational readiness.

Stronger adopted governance and protected contracts retain precedence, followed by applicable explicit task restrictions, the adopted execution-continuation protocol in its workflow domain, authenticated checkpoint plus accepted delta, and this subordinate transport procedure. Actual conflict requires diagnosis and separately authorized resolution. Do not silently repair or broaden accepted architecture. Historical draft banners are resolved by authenticated review/adoption/commit/remote bindings, never by filenames alone.

Controlling workflow: `docs/research/governance/ore-v3-execution-continuation-protocol.md`, SHA-256 `5139c876da9d3db8ddab5abb8c89673589413cb8b19406582537425d6558193f`. Adoption supplement: `docs/project-checkpoints/ore-v3-execution-protocol-adoption-continuation-supplement.md`, SHA-256 `5f5c44a3822d6e0e61aa6730b4d9f9e6e5fa47ebc5e9cbc3465141c08c8d5649`. Adoption commit `6f4c59e3871cf12c3bfc70e7ebad0dd88fb867f0`, parent `83b53e5294ad336e5b02fe0f941fb074d2d5756d`. Verify remote ancestry and the nine stronger bindings in the checkpoint. Execution Readiness v1.1, its applicable decisions, AGENTS.md, SECURITY.md, frozen F2, source/cut, acquisition, sole-reaper and receipt/settlement contracts remain controlling.

A lane starts only with a task envelope naming scope, risk, exact inputs, allowed paths/actions, prohibited actions, expected outcomes and stop conditions. A manifest locates and narrows work; it cannot authorize work beyond the user's task or stronger governance. PASS never automatically grants implementation, qualification, staging, commit, push, source activation or real-SOL authority. Uncertain risk uses the highest plausible class or stops.

## 2. Default bootstrap and evidence transport

After independent infrastructure PASS and required adoption, default: authenticate controlling comprehensive checkpoint → authenticate exact lane protocol → authenticate exact current-next-gate manifest → recover exact persisted candidate/input artifacts → execute CONTINUATION-SAFETY PREFLIGHT and emit its evidence table → execute only the separately authorized single operation if and only if CS-PREFLIGHT-PASS. Before adoption, the old accepted workflow and manual/multipart handoff remain authoritative; these drafts can be evaluated under an explicit review authorization without becoming canonical.

After accepted migration, long receipt-confirmed multipart prompts are a FALLBACK, not the default; before migration the accepted manual workflow remains available and controlling. Use them only when prompt/tool limits require it, the exact task payload is not otherwise repository-accessible, or a fresh lane cannot recover necessary persisted evidence. Retain ordering, completeness, final byte identity and explicit end-of-payload confirmation; never execute a partial relay. A relay is transport, not authority.

We are automating transport, not weakening adversarial separation. Repository-backed bootstrapping replaces manual copying; it does not replace primary evidence inspection. Conversational memory is not repository authority. Summaries are not substitutes for persisted exact candidate identities.

## 3. Common authentication and preservation contract (all seven lane classes)

Before dependent work, use `git --no-optional-locks` (or `GIT_OPTIONAL_LOCKS=0`). Authenticate repository root, branch/upstream, local HEAD, tracking HEAD, independently queried live remote HEAD, ahead/behind, staged diff and index bytes. Use read-only `ls-remote`; do not fetch or change refs. Retry transient transport failure read-only. Transport failure is not repository divergence and is not proof of equality; unresolved remote authentication blocks dependent work. Real mismatch stops the lane.

Authenticate checkpoint/protocol/manifest hashes against an external persisted creation/review/publication binding. A locally computed hash alone proves no acceptance. Authenticate accepted-result chain, exact required input bytes, governance commit/blob ancestry, and full inherited inventory plus explicitly authorized deltas. Record which deeper historical primary evidence was checked now and which was recovered through the authenticated checkpoint. Missing required primary proof is U, not reconstructed fact.

Capture every Git-visible path's content, size, mode and tracked/untracked classification, plus status/index/HEAD/refs/config/diff identities. Validate the exact mutable boundary before and after work, including allowed additions. Never reset, clean or stage to force counts. Preserve all pre-existing content unless its exact edit is separately authorized. Unexpected concurrent changes block propagation. Ignored operational storage is outside this inventory and receives no mutation authority.

For every message candidate record semantic name, session UUID, one-based JSONL record, message ID, timestamp, extraction rule, UTF-8 byte count and SHA-256. Require assistant response_item identity and matching session metadata. For file candidates record exact path, size, newline count where meaningful, SHA-256 and Git blob without staging (`git hash-object`, no `-w`). Preserve original negative evidence and prior candidate/review bindings. Review must cite the exact candidate hash, scope, outcome and exclusions. Changed bytes require a new identity and appropriate fresh review.

At completion inspect status, run `git diff --check`, check new untracked authored prose separately, and compare the full path/content/mode inventory against baseline plus authorized delta. Exact historical evidence whitespace must not be normalized. Report results and exactly one next gate. Do not mistake static document checks for runtime tests or qualification.

## 4. Lane classes

All rows inherit the authentication, candidate identity and repository-preservation requirements of §3. The specialized requirements below are mandatory in addition. A review lane is fresh and distinct from the author of the candidate it reviews; an author self-audit cannot count as independent review. Do not reuse the author lane as its own reviewer or send it a desired verdict. Reviewers remain free to FAIL or report U.

| Lane class | Purpose and allowed authority | Prohibited authority | Specific authentication / identity | Exact outcome types | Propagation gate / blocking condition | Preservation |
|---|---|---|---|---|---|---|
| AUTHOR CORRECTION LANE | Resolve one expressly scoped defect using accepted inputs; produce a persisted candidate. | Self-PASS, silent upstream repair, downstream design, unapproved implementation or governance changes. | Exact original failure/U and accepted upstream hashes; new candidate metadata under §3. | CORRECTED-CANDIDATE; U-INCOMPLETE; AUTHORITY-MISMATCH-STOP. | Completed HIGH-risk correction requires fresh independent review before propagation; incomplete candidate, new defect/scope or mismatch blocks. | Only expressly authorized artifact paths may change; otherwise response-only. Preserve failed original. |
| INDEPENDENT HIGH-RISK REVIEW LANE | Adversarially inspect exact candidate, authority, schedules and exclusions; independently decide. | Authoring repairs, assuming PASS, expanding scope, implementation or unapproved probes. | Fresh reviewer session; exact reviewed author identity and every consumed export. | PASS; FAIL with one focused defect export; U with exact missing evidence; AUTHORITY-MISMATCH-STOP. | Exact bounded PASS permits only separately authorized propagation; FAIL/U/mismatch blocks. No silent repair to achieve PASS. | Read-only unless an exact review artifact path was separately authorized; preserve candidate bytes. |
| EVIDENCE-RECOVERY LANE | Recover and authenticate complete original evidence; distinguish availability from content. | Reconstructing missing proof, changing semantics/verdicts, retroactive acceptance. | Original locator/session/record and exact extraction hash; compare established expected identities. | RECOVERED-EXACT; U-MISSING-EVIDENCE; AUTHORITY-MISMATCH-STOP. | Exact recovery permits return to the blocked gate; it never supplies semantic PASS. | Read-only by default; durable recovered copies only in authorized paths; preserve originals. |
| CHECKPOINT AUTHOR LANE | Preserve accepted chain, unresolved frontier, inventories and bootstraps at a milestone. | New architecture, self-adoption, implementation, rewriting old checkpoint or governance without authority. | Complete predecessor hash/review/publication chain, accepted pairs and new artifact identities. | CHECKPOINT-CANDIDATE; U-INCOMPLETE; AUTHORITY-MISMATCH-STOP. | Exact completed candidate routes to fresh checkpoint review; no primary-baseline supersession from self-audit. | Only named new checkpoint/package paths; old baseline remains intact. |
| CHECKPOINT REVIEW LANE | Independently verify exact checkpoint/package, provenance, completeness, gates and preservation. | Silent correction, downstream architecture, implementation, automatic publication. | Exact whole-file hashes for every package member, chain and independence. | INFRASTRUCTURE-PASS (for this three-file package) or CHECKPOINT-PASS; FAIL with one focused correction; U with missing proof; AUTHORITY-MISMATCH-STOP. | PASS applies only to reviewed bytes; adoption/publication prerequisites still govern. FAIL/U blocks baseline replacement and downstream work. | Read-only except separately authorized review report; never repair candidates in review. |
| IMPLEMENTATION LANE | Implement one separately authorized accepted architecture slice. | Choosing unresolved HIGH-risk semantics; qualification or operations beyond authorization; automatic repair after failure. | Accepted architecture/reviews, exact code baseline, authorized path list and adverse oracles. | IMPLEMENTATION-CANDIDATE; VALIDATION-FAIL-DIAGNOSED; U-BLOCKED; AUTHORITY-MISMATCH-STOP. | Required validation plus independent review and explicit reconciliation; implementation success alone is not qualification. | Exact authorized code/test/evidence delta; preserve unrelated work and first negative. Stronger no-repair rule prevails. |
| QUALIFICATION LANE | Execute only separately authorized schedules against exact accepted artifacts and governed oracles. | Inventing evidence, weakening oracles, runtime/code repair, expanding signals/process/mining scope. | Exact executable/artifact equivalence, authority, target attribution and schedule authorization. | QUALIFICATION-PASS; QUALIFICATION-FAIL; INCONCLUSIVE/U; AUTHORITY-MISMATCH-STOP. | Only exact supported claims may propagate after required independent review/reconciliation; missing proof and failures block. | Only named evidence outputs and explicitly authorized runtime effects; preserve raw negatives; no cleanup that fabricates success. |

## 5. Outcome routing and one-next-gate discipline

PASS means the exact reviewed candidate meets the bounded reviewed contract; it grants neither universal safety nor downstream permission. FAIL means a demonstrated defect; preserve the first decisive finding and export one focused correction without repairing it in review. U means insufficient authority/evidence or incomplete semantics; it is neither PASS nor an invented definitive failure. Stop dependent work and name the one focused recovery/correction needed. Authority mismatch is fail-closed STOP; diagnose, do not force reconciliation by mutation.

Every HIGH-risk completed correction requires fresh independent review before propagation. Corrected bytes invalidate an earlier candidate review. Accepted results form an immutable chain: later exports consume only accepted bounded inputs. Maintain semantic candidate names (e.g. AR-C and RR-AR-PASS) and use lane titles `STAGE3C-<scope>-AUTHOR`, `STAGE3C-<scope>-REVIEW`, or `STAGE3C-<scope>-EVIDENCE`. Include candidate hash in the handoff; a lane title is not identity.

Current package: accepted frontier RR-AR-PASS. Exactly one immediate gate is fresh independent HIGH-risk continuation-infrastructure review of the exact three authored artifacts. CD MAY NOT BEGIN until infrastructure review passes, is accepted, and required separate adoption/publication occurs. Architecture next gate after that PASS plus required adoption is focused CD author correction consuming accepted RA/WP/OA/MI/AE/AR exports; this is a routing statement, not permission to execute CD now. Infrastructure FAIL routes to one focused infrastructure correction, then fresh review. U routes to focused evidence recovery. No path automatically starts implementation.

## 6. Checkpoint rotation and effectiveness

A new comprehensive checkpoint SHOULD be triggered by an independently accepted major cross-layer architecture frontier, accepted implementation slice, accepted qualification milestone, major governance adoption/change, material protocol/control change, before context becomes materially unsafe, or before retiring a long-running coordinating chat. The controlling execution protocol's stronger mandatory milestone/context rules remain mandatory. Avoid churn after trivial operations; use compact exact evidence between milestones.

Never overwrite an old frozen checkpoint. Author, independently review exact final bytes, establish explicit acceptance/adoption and fulfill separately authorized publication requirements. For this package the old post-U1/U2/RR1 checkpoint remains the last accepted repository-backed continuation baseline until exact authoring, independent infrastructure PASS, and separately authorized adoption/commit/publication required by controlling workflow occur. No such publication is authorized here. An infrastructure PASS alone does not fabricate remote publication or change HEAD.

## 7. Anti-drift rationale

Content hashes and persisted identities prevent text substitution. Remote-backed Git identity and full mutable-boundary comparisons distinguish authority from local drift. The immutable accepted-result chain and stronger-governance precedence constrain semantics. Fresh reviewer independence preserves adversarial judgment. Explicit authority ceilings, no silent repair, a single next gate and exact PASS/FAIL/U routing constrain action. Fail-closed uncertainty prevents missing proof becoming permission. Checkpoint rotation and repository-backed bootstrapping preserve continuity when conversations are retired. Each control remains in force when transport is automated.

## 8. Compact Codex bootstrap

<!-- CODEX-BOOTSTRAP-BEGIN -->
Read/authenticate in /Users/erale/Documents/orev3:
1. Controlling accepted checkpoint: docs/project-checkpoints/ore-v3-stage3c-post-u1-u2-rr1-pass-comprehensive-continuation.md; authenticate draft review target docs/project-checkpoints/ore-v3-stage3c-post-ar-rr-ar-pass-comprehensive-continuation.md separately.
2. Exact lane protocol: docs/research/governance/ore-v3-codex-lane-handoff-author-review-protocol.md.
3. Exact current-next-gate manifest: docs/project-checkpoints/ore-v3-stage3c-current-next-gate.json.
Recover exact persisted inputs and external identity/status bindings; conversational summaries are not substitutes. All three infrastructure candidates remain DRAFT-UNREVIEWED until independently reviewed and separately adopted as required. Under a separately authorized lane task, execute CONTINUATION-SAFETY PREFLIGHT, emit the required Control | Status | Evidence table, and proceed only on CS-PREFLIGHT-PASS. Otherwise stop, name the exact failed/uncertain CS IDs and report the one manifest-defined remediation/evidence gate. A substantive answer without a valid preflight PASS is not authorized continuation. Current next gate is fresh independent HIGH-risk review of the three amended drafts; no CD, adoption or implementation is authorized. After accepted migration, authenticate the explicitly accepted successor baseline instead of assuming this historical pointer remains current.
<!-- CODEX-BOOTSTRAP-END -->

The bootstrap is not self-authenticating. Before a review, obtain the candidate identities from the persisted author report; after acceptance, obtain the exact independent review and applicable publication binding. Self/path references deliberately carry no self-hash; the manifest binds checkpoint/protocol hashes, while its own hash is bound externally by author/review reports.

## 9. Mandatory CONTINUATION-SAFETY PREFLIGHT

This is a concrete procedural interlock, not an implemented runtime enforcement service. No runtime code is authorized by this amendment. Every future lane class must execute this interlock before substantive reasoning, review judgment, correction, implementation or qualification. Authentication, read-only evidence retrieval needed to decide preflight, and reporting blockers are permitted before PASS; they may not become hidden substantive work. A missing preflight transcript is no permission. The receiving coordinator/reviewer must reject any substantive result lacking its exact valid preflight binding.

The current amendment is authorized by the user's exact three-file task under the old accepted workflow, not by this draft's own rules. Its author self-audit does not constitute independent review or adoption. The next review must test the interlock under its separate task authorization. DRAFT status alone is not a defect when the authenticated task is to review that draft; promoting it to canonical authority is AC20 and blocks.

Execute these steps in order:

1. Recover the externally authorized envelope, expected identities, current lane/session ID and accepted baseline; record all candidate author/amender IDs. Distinguish the controlling accepted old checkpoint/workflow from candidate infrastructure. Missing ordering or external authorization is U; a known forbidden action is FAIL.
2. Read §11's applicability matrix and the exact manifest `required_controls`. The effective set is their union plus stronger/task-specific required controls. The current infrastructure-review lane requires all CS01–CS25, with no N/A. A manifest may specialize applicability using the defined predicates; a lane cannot invent a reduced set, waive inconvenient controls or downgrade risk.
3. Perform the evidence checks in §10 against the exact expected state, using read-only operations where possible. Emit exactly one row for every CS01–CS25 under the columns `Control | Status | Evidence`. Allowed Status values are only `PASS`, `FAIL`, `U`, `N/A`. Evidence must state expected and observed facts, a reproducible command/result or exact artifact/session/record/hash/task-clause locator, time/order of observation, and for N/A the explicit matrix permission and proven false condition. A promise to check later is U. Unavailable evidence is U; an established mismatch/violation is FAIL. Check all available independent evidence, but never proceed substantively to resolve preflight.
4. Emit exactly one overall result: CS-PREFLIGHT-PASS, CS-PREFLIGHT-FAIL or CS-PREFLIGHT-U, applying §12. Include the lane ID, lane class, risk, exact candidate set, checkpoint/protocol/manifest revisions and hashes, expected mutable baseline, current gate, authorized delta (if any), failed/uncertain control IDs and exactly one resulting gate. This persisted preflight record is consumed by completion and propagation checks. It is a transcript/report, not permission to create an unapproved repository artifact.
5. Only CS-PREFLIGHT-PASS opens the authorized substantive operation. Any later relevant protected-state change expires it pending §13 revalidation. CS-PREFLIGHT-FAIL/U close the gate immediately. They permit only blocker reporting and the explicitly scoped remediation/evidence gate under separate compatible authorization; no automatic repair or continuation.

There is no “continue carefully”, “mostly passed” or “best effort despite mismatch” mode. No aggregate score, majority rule or weighted acceptance exists. All required controls are consequential.

The preflight's own PASS is not the substantive review PASS and never proves the candidate safe. A reviewer can pass entry preflight and then FAIL its target for a semantic flaw or an adversarial case. If entry preflight finds a defect, it reports that defect without continuing substantive review. Read-only evidence recovery to complete the current preflight does not confer downstream execution authority.

## 10. Stable control definitions

Stable IDs are frozen. CS01–CS25 must never be reused for another meaning. A material definition change or weakening requires a new protocol revision, explicit change record and fresh independent infrastructure review before adoption. Old meanings/identities remain recoverable. No normal task manifest may weaken these definitions.

| Control | Stable definition | Required evidence |
|---|---|---|
| CS01 — REPOSITORY IDENTITY | Resolve expected repository root and Git identity: /Users/erale/Documents/orev3, expected origin and authenticated commit history; a same-named directory is insufficient. | Exact command/result, artifact/record/hash or explicit task-clause locator; no assertion-only PASS. |
| CS02 — BRANCH / UPSTREAM | Authenticate current branch and configured upstream against the task envelope; both must match. | Exact command/result, artifact/record/hash or explicit task-clause locator; no assertion-only PASS. |
| CS03 — REMOTE-BACKED HEAD | Compare local HEAD, tracking HEAD and independently queried live-remote HEAD with the authorized expectation. Transport failure is U, neither divergence nor equality; recovered evidence must be fresh before reliance. | Exact command/result, artifact/record/hash or explicit task-clause locator; no assertion-only PASS. |
| CS04 — AHEAD / BEHIND | Authenticate exact expected ahead/behind counts; do not infer synchronization from a branch name. | Exact command/result, artifact/record/hash or explicit task-clause locator; no assertion-only PASS. |
| CS05 — INDEX BOUNDARY | Authenticate index hash and staged diff against the authorized boundary. Unexpected staged content or index drift blocks execution. | Exact command/result, artifact/record/hash or explicit task-clause locator; no assertion-only PASS. |
| CS06 — MUTABLE WORKTREE BOUNDARY | Authenticate exact tracked-modification and untracked-path sets and classifications, not counts alone. | Exact command/result, artifact/record/hash or explicit task-clause locator; no assertion-only PASS. |
| CS07 — INVENTORY / MANIFEST | Authenticate Git-visible path set, bytes, sizes and modes, and the required path/content/mode digest plus exact authorized delta. Missing identities cannot be replaced with matching counts. | Exact command/result, artifact/record/hash or explicit task-clause locator; no assertion-only PASS. |
| CS08 — CONTROLLING CHECKPOINT | Authenticate exact controlling checkpoint identity and independent acceptance/publication status. Distinguish an accepted baseline from a DRAFT-UNREVIEWED candidate being reviewed. | Exact command/result, artifact/record/hash or explicit task-clause locator; no assertion-only PASS. |
| CS09 — LANE PROTOCOL | Authenticate exact lane-protocol path, revision, bytes/hash/blob and effective status against external authority. A draft may be inspected under an authorized review envelope; it is not canonical. | Exact command/result, artifact/record/hash or explicit task-clause locator; no assertion-only PASS. |
| CS10 — NEXT-GATE MANIFEST | Authenticate exact manifest revision/status and externally bound whole-file identity. Its contents cannot authorize themselves. | Exact command/result, artifact/record/hash or explicit task-clause locator; no assertion-only PASS. |
| CS11 — STRONGER GOVERNANCE | Authenticate required stronger-governance bindings, domain applicability and precedence; no workflow convenience overrides them. | Exact command/result, artifact/record/hash or explicit task-clause locator; no assertion-only PASS. |
| CS12 — ACCEPTED FRONTIER | Authenticate the exact independently accepted frontier and all consumed author/PASS bindings; current frontier is RR-AR-PASS. | Exact command/result, artifact/record/hash or explicit task-clause locator; no assertion-only PASS. |
| CS13 — EXACT CANDIDATE IDENTITY | Authenticate each consumed persisted message by session UUID, record, message ID, timestamp, extraction rule, UTF-8 bytes and SHA-256; each file candidate by path/revision/status/bytes/hash/blob and external author binding. | Exact command/result, artifact/record/hash or explicit task-clause locator; no assertion-only PASS. |
| CS14 — AUTHOR / REVIEWER SEPARATION | Authenticate current reviewer session identity against every author/amender session of the reviewed candidate. A renamed task or reused author lane is not independent. | Exact command/result, artifact/record/hash or explicit task-clause locator; no assertion-only PASS. |
| CS15 — REVIEWER FREEDOM TO FAIL | Verify task/envelope permits PASS, FAIL and U, includes no required positive verdict, and does not suppress decisive adverse findings. | Exact command/result, artifact/record/hash or explicit task-clause locator; no assertion-only PASS. |
| CS16 — NO SILENT REPAIR | Verify review is of exact frozen bytes without supplementation, repair or reinterpretation to achieve PASS; any correction returns to an authorized author lane and fresh review. | Exact command/result, artifact/record/hash or explicit task-clause locator; no assertion-only PASS. |
| CS17 — AUTHORITY CEILING | Authenticate the exact task-specific allowed actions/paths, prohibited authority and stop conditions; the manifest cannot enlarge the user envelope. | Exact command/result, artifact/record/hash or explicit task-clause locator; no assertion-only PASS. |
| CS18 — EXACTLY ONE NEXT GATE | Authenticate exactly one currently enabled substantive operation. Conditional future gates and failure routing are disabled alternatives, never concurrent authority. | Exact command/result, artifact/record/hash or explicit task-clause locator; no assertion-only PASS. |
| CS19 — NO IMPLICIT IMPLEMENTATION | Verify architecture PASS does not confer implementation, qualification or operational permission; each requires its own exact authorization. | Exact command/result, artifact/record/hash or explicit task-clause locator; no assertion-only PASS. |
| CS20 — OUTCOME ROUTING | Authenticate deterministic PASS/FAIL/U routing and the distinction between preflight permission and substantive review success. FAIL/U cannot propagate success downstream. | Exact command/result, artifact/record/hash or explicit task-clause locator; no assertion-only PASS. |
| CS21 — TASK-SPECIFIC ADVERSARIAL BURDENS | Authenticate complete task-specific HIGH-risk attack requirements and expected oracles before work; a generic safety claim is insufficient. | Exact command/result, artifact/record/hash or explicit task-clause locator; no assertion-only PASS. |
| CS22 — CHECKPOINT ROTATION | Authenticate accepted checkpoint lineage/publication and known successors; the selected accepted checkpoint must not be superseded. Unresolved successor evidence is U. | Exact command/result, artifact/record/hash or explicit task-clause locator; no assertion-only PASS. |
| CS23 — STALENESS CHECK | Authenticate that checkpoint, protocol, manifest, candidate identities and accepted frontier are mutually current for this exact task and accepted-delta chain. | Exact command/result, artifact/record/hash or explicit task-clause locator; no assertion-only PASS. |
| CS24 — SELF-CONSISTENCY | Check all controlling artifacts and task envelope agree on frontier, checkpoint, protocol, next gate, authority and prohibited work; distinguish literal historical evidence from current bindings. | Exact command/result, artifact/record/hash or explicit task-clause locator; no assertion-only PASS. |
| CS25 — FALLBACK AVAILABILITY | Verify an exact manual/multipart handoff remains available when repository-backed bootstrap lacks necessary task context; unresolved capacity to convey required exact evidence blocks work. | Exact command/result, artifact/record/hash or explicit task-clause locator; no assertion-only PASS. |

Evidence sufficiency details: CS01–CS07 must record actual Git/filesystem command results and expected boundary, not prose assurances. CS08–CS13 must authenticate external trust bindings and exact bytes, not hashes merely copied from the same file. CS14 uses session metadata plus persisted author/amendment reports; session titles alone fail. CS15–CS21 cite exact task/manifest/protocol clauses and verify no contradictory authorization. CS22–CS24 inspect repository checkpoint lineage and authenticated later acceptance/adoption/publication records in the available continuation authority channel; filenames/mtime and conversational claims do not establish supersession. If completeness/currentness cannot be established, report U. CS25 identifies the available manual/task-message transport and explains how necessary exact context can be relayed with receipt confirmation; fallback cannot waive missing authority.

## 11. Lane-class applicability matrix

R = REQUIRED; P = PERMITTED-N/A; C = CONDITIONAL under the predicates below. R controls must be PASS. P does not require N/A: if a lane actually performs the relevant independent-review role, that role's R matrix applies. Every N/A needs explicit evidence; uncertainty about applicability is U, never N/A.

| Lane class | CS01–CS12 | CS13 | CS14–CS16 | CS17–CS20 | CS21 | CS22–CS25 |
|---|---|---|---|---|---|---|
| AUTHOR CORRECTION LANE | R | C | P | R | C | R |
| INDEPENDENT HIGH-RISK REVIEW LANE | R | R | R | R | R | R |
| EVIDENCE-RECOVERY LANE | R | C | P | R | C | R |
| CHECKPOINT AUTHOR LANE | R | R | P | R | C | R |
| CHECKPOINT REVIEW LANE | R | R | R | R | C | R |
| IMPLEMENTATION LANE | R | R | P | R | C | R |
| QUALIFICATION LANE | R | R | P | R | C | R |

CS13 C becomes REQUIRED whenever any persisted candidate/result is consumed as an authoritative premise. N/A is permitted only when there is none, with the exact task scope proving that absence. Evidence recovery may search for a missing target without pretending to have authenticated its missing bytes: its expected locator/hash and known governing inputs are authenticated, the target remains unavailable and cannot be consumed until recovered. This distinction cannot waive missing required authority for the recovery operation itself.

CS14–CS16 P applies only to a non-review lane; no independent review is being claimed. Their N/A does not permit false acceptance or silent upstream repair: §1, CS17 and CS20 still forbid those. If a task includes review, the review requirements apply to that portion and author self-review cannot satisfy independence.

CS21 C becomes REQUIRED for every task-specific HIGH-risk lane, every infrastructure/control review or correction, and whenever stronger governance or explicit task requires adverse burdens. It is PERMITTED-N/A only for a provably non-HIGH task with no such burden. Uncertain risk uses the highest plausible class or stops. Current CHECKPOINT REVIEW LANE is HIGH risk: all 25 controls REQUIRED, no conditional exemption and no N/A.

## 12. Fail-closed oracle and deterministic routing

CS-PREFLIGHT-PASS if and only if every required/effectively required control is PASS, every N/A is explicitly permitted by §11 with proved applicability, no FAIL or U remains in an applicable control, no cross-artifact contradiction exists, exactly one current substantive next gate is unambiguous, required candidate identities authenticate, and the authority ceiling is exact. An omitted/duplicate/invalid-status row or a missing mandatory constraint is an established violation, not an implied PASS.

CS-PREFLIGHT-FAIL when an actual contradiction, stale identity, unauthorized drift, forbidden lane reuse, missing mandatory constraint or other control violation is established. If both established violations and unresolved evidence exist, emit the single overall FAIL while retaining all FAIL/U rows; no evidence is discarded.

CS-PREFLIGHT-U when no established violation resolves the overall result to FAIL but required evidence is unavailable, authoritative ordering/identity is uncertain, or an applicable control cannot be resolved. Remote transport failure alone is CS03 U: stop equality-dependent execution, retry/recover read-only if authorized, and never label transport failure itself repository divergence.

Current package routing:

| Result | Exactly one next gate; no automatic execution |
|---|---|
| CS-PREFLIGHT-PASS | Only the separately authorized fresh independent HIGH-risk infrastructure review of the exact three drafts. No CD. |
| CS-PREFLIGHT-FAIL | One focused infrastructure/authority correction gate limited to the recorded established violation(s), beginning with diagnosis. If the flaw is repository/identity drift, preserve evidence and obtain an explicit authorized resolution; never normalize the baseline or repair unrelated files. Fresh full preflight and independent review are required before propagation. |
| CS-PREFLIGHT-U | One focused evidence-recovery gate for the exact unresolved CS IDs; no substantive candidate review, CD or baseline supersession. |

These gates are mutually exclusive routes, not simultaneous operations. When several IDs fail, report them all in one bounded gate; inability to define a compatible narrow correction remains blocked, not authority to split into unauthorized operations. A substantive infrastructure review independently routes INFRASTRUCTURE-PASS to required separate adoption/publication, FAIL to one focused correction, U to one focused evidence-recovery gate. It never starts CD in the review lane.

## 13. Periodic revalidation and protected drift

Execute the full applicable preflight at lane entry. Immediately before every authorized mutation, revalidate all controls whose evidence could change, including CS01–CS13, CS17–CS24 and lane identity/independence if the actor changed; explicitly carry forward only still-valid unchanged evidence. Before separately authorized staging/commit/push, revalidate the complete applicable set against the explicitly authorized transition and exact intended diff. No publication authority exists in the current package.

At lane completion and before propagating any PASS downstream, revalidate the full applicable set, authenticate actual output identities, compare the exact authorized delta and bind the completion record to the entry record. The downstream receiving lane must independently run its own entry preflight. For long-running work, pause and revalidate repository/checkpoint/protocol/manifest authority whenever state could materially change, including external edits, new remote observations, changed tasks/inputs, pauses or resumed context. An entry PASS is not permanent authority.

Intentional mutations are checked against a previously authorized exact path/action envelope and preserved originals. After a permitted change, freeze actual final identities and the comparison evidence; a changed candidate invalidates its old review. Never absorb unexpected drift into the expected state. A task envelope can authorize a specific HEAD/index transition, but it cannot guess future identity or waive verification afterward.

Protected drift includes repository identity, branch/upstream, remote-backed HEAD expectation, ahead/behind, index, mutable boundary, inventory/manifest, accepted candidate identities, checkpoint/protocol/manifest identity, stronger-governance bindings, accepted frontier and current gate. Classify only:

- EXPECTED-AUTHORIZED: exact change traceable to prior explicit scope and authenticated resulting identity; still requires revalidation.
- UNEXPECTED-BLOCKING: established unauthorized change; FAIL and stop.
- UNCERTAIN-BLOCKING: unexplained or unprovable change/ordering; U and stop.

Do not automatically normalize, repair, reset, ignore or absorb unexpected/uncertain drift into a fresh baseline. Read-only diagnosis is not permission to modify unrelated state.

## 14. Status, fallback, rollback and non-circular identities

Stable infrastructure status vocabulary: DRAFT-UNREVIEWED, REVIEWED-PASS, SUPERSEDED. All three amended artifacts are DRAFT-UNREVIEWED. None is yet accepted continuation authority. The old accepted post-U1/U2/RR1 checkpoint remains the practical baseline until independent infrastructure PASS and separately authorized adoption/commit/publication required by controlling workflow.

Before that migration, manual/multipart handoff under the old accepted workflow is authoritative fallback and the three files are experimental draft infrastructure. After review plus required adoption, repository-backed bootstrap becomes default; manual/multipart remains available whenever exact context cannot otherwise be conveyed. Missing authoritative evidence still blocks in either transport.

If a material flaw is discovered later: freeze downstream propagation; authenticate the last independently accepted checkpoint/protocol; identify defective infrastructure as under correction (a work disposition, not a fourth status) or SUPERSEDED when an authenticated replacement exists; revert operational coordination to the last accepted workflow; perform one separately authorized focused infrastructure correction; require fresh independent infrastructure review and required adoption before readoption. Operational rollback does not mean git reset, history rewriting or automatic repository edits. Convenience cannot require continued use of a defective workflow.

Identity graph, computed in order: finalize protocol → checkpoint binds protocol path/revision/status/bytes/SHA-256/blob → manifest binds checkpoint and protocol path/revision/status/bytes/SHA-256/blob → external persisted amendment report and independent review bind final whole-file identities of all three. Checkpoint records only manifest path/revision/expected role/status. Protocol can name paths/revisions and external binding rules but never hashes a dependent artifact. Manifest records its own path/revision/status, never its own final hash. The whole-inventory digest that includes these drafts is also external; its internal validation rule uses the preserved 708-path baseline plus the three externally bound final identities. This is a directed acyclic identity graph, not a hash fixed point.

For review bootstrap, the exact external amendment report supplies final draft identities and author session; the separately issued review task under the old accepted workflow supplies permission. A draft manifest cannot mint that permission. Independent review records session identity, preflight evidence, exact all-three bytes/hashes/blobs, verdict and exclusions. After a PASS, immutable in-file DRAFT-UNREVIEWED describes authored status; an exact external review/adoption record may establish effective REVIEWED-PASS for those same bytes. A cosmetic in-file status edit would change identity and must not inherit the old byte-level review without explicit fresh binding/review. A later accepted replacement establishes SUPERSEDED through an authenticated lineage record. Never infer effective acceptance from a status label alone.

## 15. Adversarial validation of continuation controls

The upcoming independent HIGH-risk infrastructure review must test BOTH continuation-content correctness and safety-control correctness. It must authenticate checkpoint completeness, accepted RA→WP→OA→MI→AE→AR chain and exact RR-AR-PASS, unresolved CD, protocol and manifest semantics, cross-artifact consistency, all AC01–AC20 cases, preflight PASS/FAIL/U oracle, rollback, live canary, DRAFT status and the acyclic identity scheme.

For each case emit `Case | Evidence / counterfactual input | Observed gate decision | BLOCK or INCORRECTLY-ALLOW`. Every consequential adverse case must classify BLOCK for infrastructure PASS. This author table is an expected oracle, not an executed independent test result. If the reviewer cannot resolve a case, its substantive result is U and it cannot claim all cases BLOCK. Do not fabricate a classification from expectation alone.

Review probes are read-only counterfactual/tabletop evaluations of the procedural gate using exact clauses, supplied observations and decision traces, or separately authorized isolated fixtures. They must not actually switch this repository's branch, stage files, corrupt candidates, change refs or create unapproved repository paths. No runtime qualification is implied. A correctly handled unavailable remote yields U and BLOCK until fresh authoritative evidence is recovered.

| Case | Adverse condition | Controls | Expected preflight result | Required review classification |
|---|---|---|---|---|
| AC01 | wrong repository path | CS01 | CS-PREFLIGHT-FAIL | BLOCK |
| AC02 | wrong branch | CS02 | CS-PREFLIGHT-FAIL | BLOCK |
| AC03 | local/tracking/live-remote HEAD mismatch | CS03 | CS-PREFLIGHT-FAIL | BLOCK |
| AC04 | remote transport failure | CS03 | CS-PREFLIGHT-U; not divergence or equality | BLOCK |
| AC05 | unexpected staged file | CS05 | CS-PREFLIGHT-FAIL | BLOCK |
| AC06 | unexpected tracked modification | CS06/CS07 | CS-PREFLIGHT-FAIL | BLOCK |
| AC07 | unexpected untracked path in frozen boundary | CS06/CS07 | CS-PREFLIGHT-FAIL | BLOCK |
| AC08 | stale checkpoint hash | CS08/CS23 | CS-PREFLIGHT-FAIL | BLOCK |
| AC09 | stale manifest identity | CS10/CS23 | CS-PREFLIGHT-FAIL | BLOCK |
| AC10 | protocol hash mismatch | CS09 | CS-PREFLIGHT-FAIL | BLOCK |
| AC11 | candidate hash mismatch | CS13 | CS-PREFLIGHT-FAIL | BLOCK |
| AC12 | author lane reused as reviewer | CS14 | CS-PREFLIGHT-FAIL | BLOCK |
| AC13 | two substantive next gates | CS18 | CS-PREFLIGHT-FAIL | BLOCK |
| AC14 | missing task-specific adversarial burdens | CS21 | CS-PREFLIGHT-FAIL | BLOCK |
| AC15 | architecture PASS treated as implementation authorization | CS17/CS19 | CS-PREFLIGHT-FAIL | BLOCK |
| AC16 | FAIL allowed to propagate downstream | CS20 | CS-PREFLIGHT-FAIL | BLOCK |
| AC17 | U treated as PASS | CS20 | CS-PREFLIGHT-FAIL | BLOCK |
| AC18 | reviewer silently repairs candidate | CS16 | CS-PREFLIGHT-FAIL | BLOCK |
| AC19 | stale accepted frontier | CS12/CS23 | CS-PREFLIGHT-FAIL | BLOCK |
| AC20 | DRAFT-UNREVIEWED infrastructure treated as canonical | CS08/CS09/CS10/CS24 | CS-PREFLIGHT-FAIL | BLOCK |

Also check a valid draft-review envelope can proceed through entry preflight without treating the draft as accepted authority; and a purported substantive answer without an authenticated preflight PASS is rejected. These positive/control observations distinguish a working fail-closed mechanism from an unconditional refusal. The review retains freedom to identify additional consequential adversarial cases within its authorized scope.

## 16. Validation of the validation system and live canary

Future comprehensive checkpoints must record the accepted lane-protocol revision, exact accepted protocol identity/hash, stable CS set and control-definition changes, last independently reviewed protocol identity, accepted exceptions (with exact authority and scope), and current infrastructure status. No unspecified exception exists. A normal manifest may specialize applicability only under §11; it cannot weaken control definitions. Any material weakening or change to a consequential control requires fresh independent infrastructure review before adoption, even if called documentation maintenance.

Checkpoint rotation SHOULD follow independently accepted major cross-layer architecture, accepted implementation slices, accepted qualification milestones, major governance adoption/change, material protocol/control change, unsafe context risk and retirement of a long-running coordinating chat. Avoid trivial churn; stronger mandatory rotation rules still apply. CS22/CS23 must detect pointers to superseded accepted infrastructure and block unresolved lineage/currentness.

After independent infrastructure PASS plus required separate adoption, the FIRST real architecture lane, expected focused CD correction, is a LIVE CANARY. Before ANY CD reasoning it must authenticate accepted checkpoint/protocol/manifest and required adoption bindings, execute the full required CS preflight, emit the table, and establish CS-PREFLIGHT-PASS. The future CD task must include its own HIGH-risk task-specific burdens; this infrastructure manifest cannot stand in for that task or serve as an unchanged CD authorization.

If required controls fail, the reviewed protocol behaves differently, cross-artifact semantics disagree, or safeguards cannot be reproduced, STOP before CD reasoning. Established mismatch routes to one focused infrastructure correction; unavailable proof routes to one focused evidence recovery (FAIL has precedence when both occur). No CD reasoning may proceed. Report canary evidence for later independent acceptance; a canary is not independent review of its own architecture or permission for implementation.
