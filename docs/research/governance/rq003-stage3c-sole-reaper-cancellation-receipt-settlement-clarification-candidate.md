# Stage 3C Sole-Reaper Cancellation Receipt and Episode Settlement Clarification

**SUPPLEMENTARY GOVERNANCE CLARIFICATION CANDIDATE — INDEPENDENT REVIEW REQUIRED — NOT ADOPTED — NOT GIT-EFFECTIVE — NO IMPLEMENTATION OR EXPERIMENT AUTHORITY**

Drafted 2026-09-08 under authorization to create this file only.

## 1. Purpose, status and exact scope

This candidate proposes one policy choice for the adopted sole-reaper cancellation
episode: legitimate owner receipt, ordered against clean settlement, determines
request membership. It addresses a supported event becoming OS/interpreter-pending
during action delivery but reaching its callback and owner receipt after proposed
settlement. It does not claim the adopted text already uniquely requires this choice.

MUST/MUST NOT statements below are proposed normative requirements only. Independent
review, explicit separate adoption and Git effectiveness remain necessary before
they change authority. Drafting and review alone authorize no implementation,
experiment, staging, commit, push, reference change or operational activity.

The supplementary scope is the meaning of receipt, arrival, later independence
and episode settlement for that delayed-request history under the existing sole
reaper. This document does not select a cancellation-owner implementation, broker,
signal mechanism, native adapter, actor attachment or shutdown design. It creates
no new public status/error, process, protocol, queue format or persistent artifact.

## 2. Authenticated authority and starting baseline

The immediate authority is
[Stage 3C Sole-Reaper Interruption and Same-Handle Admission Clarification](rq003-stage3c-sole-reaper-interruption-admission-clarification-candidate.md),
especially §§8, 10 and 12. Its exact repository path is
`docs/research/governance/rq003-stage3c-sole-reaper-interruption-admission-clarification-candidate.md`.
Identity: 36805 bytes, 523 lines, SHA-256
`f14f12ab404e806bc7d0a916a1bc1ca4583720c128c1e89b2397477bdc6dc9b0`,
Git blob `f113db63fc2d3c277048d4a8d9d03f8e19fa0213`, mode 100644.
Working, index and committed bytes were authenticated. Its candidate-status prose
is historical: explicit exact-byte adoption and the authenticated commit/publication
transition established its effectiveness. This new supplement remains unadopted.

| Repository property | Verified before drafting |
| --- | --- |
| Repository | `/Users/erale/Documents/orev3` |
| Branch / upstream | `research/post-v1` / `origin/research/post-v1` |
| Local / tracking / independently queried live remote HEAD | `1fef9920e4910996f53c17ae1944b5b79700e5b9` |
| Sole parent | `ad92eeab8ca0000509069a170369f7ecd20a14f9` |
| Subject | `Adopt Stage 3C sole-reaper interruption and admission clarification` |
| Complete commit change | One addition: the immediate-authority path above |
| Ahead / behind | 0 / 0 |
| Index | Empty |
| Mutable population | 5 tracked modifications + 27 untracked = 32 |
| Existing preservation population | 697 unique paths |
| `git diff --check` | Pass |

The live branch was queried independently with read-only `git ls-remote`; no fetch
or reference change was used to establish equality.

The comprehensive checkpoint is
`docs/project-checkpoints/ore-v3-stage3c-cross-layer-frozen-comprehensive-continuation-candidate.md`:
133128 bytes, 1156 lines, SHA-256
`9074543bb4c5b64576f01897c55b1945a163ce532e1b940ed4f140ab0f227a90`.
It equals HEAD and its committed binding at
`ff36b9a1a1afd1814f0e676565ae4d3fb49b7f93`. Its seven controlling documents were
authenticated from its inventory, including unchanged working/HEAD bytes, their
listed committed bindings and ancestry of current remote-backed HEAD:

| Governance filename under `docs/research/governance/` | SHA-256 | Git-effective binding |
| --- | --- | --- |
| `rq003-experiment-005-bounded-streaming-source-processing-prerequisite-v1.md` | `ce09153fc98145f3fa318a9c7e8dd563afbf4b64496e64535b27c49c93af90e3` | `a46173a0420d0bfd4babd17cd1ebbaa911bce241` |
| `rq003-stage3c-recovery-permission-clarification-candidate.md` | `7df413610a54adcacb06f5c01dc43b7ce2c04c5244922519871d745c0395f716` | `045c041453d232e1288e6031fc528d61f8989caa` |
| `rq003-stage3c-category-attribution-clarification-candidate.md` | `2e735f2ffe1b4d537495dd7db62d75e21bb6db822c20863f5dc29781c508c101` | `95295a8bd074d803e9405a533915b5592a484ae7` |
| `rq003-stage3c-admission-serialization-clarification-candidate.md` | `56b4e402a9b4e62853e285be3ed7ca7b7c2d1a0d34d71a7c9ee757b8dffdcfed` | `a7f0ea131237fd6f073f14a3d2fc8544920e6aba` |
| `rq003-stage3c-acquisition-lifetime-clarification-candidate.md` | `1e2c235f11689cd64c65840b3055f377ebef8d9614ea31574e398a15bf29fdcd` | `fcc2f3f42c94c691b65012fab9d0c75bebc4ef94` |
| `rq003-stage3c-controller-retirement-status-clarification-candidate.md` | `d9bf01b2449b1819545ef4c186407eb0c16c929534d6ff4bc2f37b8a4b33a304` | `d14b516277441a3849525014a92c09529347eadb` |
| `rq003-stage3c-worker-pinned-input-acquisition-lifetime-clarification-candidate.md` | `be25dd7422e10c6dc775bb3fabbfc0688c71606fdaf8196305f1282208628a9c` | `90018eeb54cb1e8590f526f72579ba262dd868d4` |

Together with the immediate reaper clarification these are eight existing controlling
documents. None is modified by this candidate. Their prerequisites and unrelated
requirements remain authoritative; a conflict requires separate resolution.

All 28 promoted implementation paths were checked at baseline commit
`ad92eeab8ca0000509069a170369f7ecd20a14f9` against the checkpoint's frozen inventory.
The checkpoint's 695 Appendix-A paths, the checkpoint itself and the adopted reaper
clarification reconcile to exactly 697 unique existing paths. Appendix identities
for the two intentionally modified paths were authenticated through HEAD; their
paused working identities were checked separately:

| Paused working path | Bytes | SHA-256 |
| --- | ---: | --- |
| `src/orev3/execution/runtime.py` | 170595 | `ff833dbd187c65456c3ac1d54a2ab2da19451906f5593184ea0bcddb7e610359` |
| `tests/execution/test_phase3b_worker_boundaries.py` | 305261 | `00d0801b0fc516df35fb99cab1b67ffce5c6f13b42cd30de523c103b07189a30` |

These are preservation inputs containing paused work, not approved implementation.
All other appendix bytes, including required prior checkpoint/RFC/bootstrap authority
and unrelated work, matched. The unrelated population remains three tracked RFC/backlog
modifications plus 27 untracked research documents. A before-state manifest retains
the 697 paths' hashes, file types/modes and relevant index/status classifications
in assessment-session memory. Ignored operational storage and live processes are
outside this inventory and are not inspected or manipulated for stable identities.

## 3. Exact gap and historical distinction

The adopted §8 requires finite explicit supported sources and coverage of
interpreter-pending delivery. Section 10 uses received/accepted requests, requests
arriving during delivery, subsumption and later independent cancellation after clean
completion. It does not explicitly choose the membership boundary for this history:

```text
first request accepted by its legitimate owner
  -> first selected action starts
  -> second event becomes OS/interpreter-pending
  -> first action completes
  -> proposed clean settlement
  -> second callback and first qualified owner receipt occur
```

The history separates an event's pending existence in the runtime from a request
already retained under owner authority. The adopted text does not uniquely say
whether the earlier runtime event or later owner receipt determines membership.
This supplement proposes the latter, subject to the anti-deferral and whole-lifetime
requirements below. This is a policy choice, not a reinterpretation of old evidence
as proof that the original text already selected it.

This gap differs from the already-established failure of two actual action
invocations while the first delivery remains active. That behavior remains prohibited
under either interpretation. The failed prototype is not retroactively compliant,
approved or frozen. The history above and the H1–H8 table are normative design
examples, not newly executed experimental evidence; no prototype or broker experiment
was run during this drafting task.

## 4. Proposed qualified owner-receipt rule

Episode membership MUST be established at the legitimate cancellation owner's
qualified ingress/receipt boundary, ordered against episode settlement. Receipt is
the authoritative ingress at which a supported request first becomes retained and
governed by that owner. The owner is the already-legitimate cancellation authority
under the adopted actor/lifetime contract; naming an object a broker does not make
it that owner or confer execution authority.

Receipt and its episode classification MUST form one logically indivisible operation
relative to settlement. There must be a complete classification, not retained but
unclassified intent that a later discretionary acceptance step can assign at will.
An implementation may choose its mechanism but MUST demonstrate the ordering it
claims. No particular lock, queue, native primitive, Python flag or public state enum
is required. Implementation freedom does not permit undecided membership.

Physical generation time alone, an OS/interpreter pending indication not yet received
by the owner, harness timestamps and discretionary later acceptance are not membership
authority. Callback entry is not automatically source generation or qualified receipt.
A source-specific contract must identify their relationship; a callback cannot be
treated as received at entry for one history and at later processing for another.

For receipt and settlement operations that overlap, qualification MUST demonstrate
one ordering consistent with every completed prior operation. A receipt completed
before settlement begins cannot be classified afterward; settlement completed before
receipt begins cannot be undone by later classification. Overlapping operations may
be ordered on either side only through the proven ingress/settlement contract, never
by convenient post-hoc labeling. The request is neither duplicated nor lost.

## 5. Source ingress and prohibition on delayed acceptance

For every admitted supported source, the implementation MUST provide a finite,
explicit mapping describing:

1. The legitimate owner and any participating source adapter acting on its behalf.
2. The precise qualified ingress, including its relationship to callback entry,
   runtime delivery and any adapter retention.
3. How received intent and its episode membership become retained together.
4. How receipt is ordered against settlement, including overlapping operations.
5. How same-thread reentry and concurrent receipt preserve that same ordering.
6. How supported delivery remains covered before, during and after the episode,
   including required restoration and final owner/capability shutdown.

A supported callback/adapter MUST enter the receipt protocol without arbitrary
application-level postponement, filtering or an acceptance decision that changes
membership. Required ingress work may implement the qualified ordering; it may not
be used to shift known intent across settlement for convenience. Known participating
retention cannot be described as mere runtime-pending state to evade the rule.

Where a participating source adapter queues or retains a cancellation request on
behalf of the owner, that retention MUST participate in qualified receipt and retained
classification. It cannot be ignored until a later dequeue to manufacture a fresh
request. The source contract must cover such earlier retention even if the main
owner callback has not yet run. Later parsing, callback execution, dispatch or dequeue
cannot overwrite already-established membership.

A source lacking the required ingress contract is a qualification limitation for
the proposed implementation. It is not permission to omit required SIGINT coverage,
drop supported pending delivery, ignore a difficult source or relabel it as unsupported
solely to make an implementation pass. Existing source eligibility remains fixed;
the implementation must establish the required contract or remain blocked.

## 6. Membership outcomes and explicit delayed-event tradeoff

| Receipt relative to clean settlement | Proposed required classification |
| --- | --- |
| A. Qualified receipt before clean settlement while the episode is active | An eligible repeated request belongs to that episode and is subsumed under the adopted eligibility rules; it does not start another action. |
| B. First qualified receipt after clean settlement | A fresh owner-received request, governed by applicable ordinary or next-episode delivery rules. It cannot be silently discarded as already handled. |
| C. Earlier generation/runtime-pending indication without earlier qualified receipt | Does not retroactively attach the request to the closed episode. Classification occurs at qualified receipt. |
| D. Earlier qualified receipt already retained, processing later | Earlier membership survives. Later processing does not make the request fresh. |
| E. Receipt overlapping settlement | The demonstrated ordering under §4 determines old versus fresh membership exactly once, with neither loss nor duplication. |

The behavioral tradeoff is explicit: an event generated during an earlier action
may require fresh delivery if its owner first receives it after clean settlement.
This is owner-receipt-based membership, not physical generation-time coalescing.
The event is not called newly generated merely because it is newly owner-received.

For this interpretation, later independent cancellation means a fresh qualified
owner receipt ordered after genuinely clean settlement, without a prior retained
membership for that request. It does not require an unobservable assertion that
the physical event was causally independent of the earlier action. Conversely, an
already-received request cannot be relabeled independent by delayed processing.

Fresh cancellation carries only the authority of the applicable existing ordinary
or later cancellation rules. It MUST NOT reopen permanently closed native admission,
create another `os.waitpid` operation for the terminal handle, approve a replacement
waiter or require constructing a new reaper episode for that same handle.

The existing subsumption conditions remain: admitted sources must mean cancellation
of the same enclosing work and require no independent per-request side effect.
This supplement does not broaden eligibility or permit coalescing non-subsumable
requests. Failed/incomplete settlement is not clean settlement and cannot be used
as the boundary that legitimizes fresh action invocation or healthy reuse.

## 7. Clean settlement and retained obligations

Clean settlement MUST be an authoritative completed transition, not an early flag.
It requires all of the following under the adopted authority:

- Required terminal reaper evidence/disposition is retained independently of caller
  receipt, and native admission remains permanently closed.
- Required protection restoration and teardown are actually resolved and verified;
  there is no caller-visible live protection context or healthy incomplete state.
- Invocation of the selected action is established, and its governed return or
  intended-raising completion has been accounted for.
- Every eligible request already received into that episode has a retained delivered
  or subsumed disposition under the existing at-most-once action rule.
- No unresolved required delivery, uncertain invocation or incomplete restoration
  is represented as successful completion.

An action still executing MUST NOT be classified as cleanly settled merely to permit
another action invocation. Clearing an active flag before return, or at the start of
exception handling without accounting for completion, is not settlement evidence.
An intended cancellation exception counts as delivery under adopted §10; it does not
authorize a replay. Uncertainty whether the selected action was invoked is not proof
that it was absent and MUST NOT justify automatic reinvocation.

The settlement transition MUST preserve requests ordered after it. Stale clearing
cannot erase a fresh receipt or overwrite its disposition. Equally, an implementation
MUST NOT retain an indefinitely active episode that absorbs future cancellation after
its obligations have actually settled. Clean completion must leave later independent
cancellation deliverable under the applicable restored behavior.

An empty application queue or absence of owner-received requests is not proof of
OS/runtime quiescence. This semantic allows classification of a later receipt without
requiring a source-generation timestamp merely to decide H2. It does not prove that
pending runtime delivery can safely be ignored, that a source adapter can be released,
or that the executable can shut down its cancellation owner.

## 8. Normative history table

These are required outcomes for future review and evidence, not experiments executed
by this candidate. Eligibility always means the unchanged adopted subsumption rules.

| History | Proposed required outcome |
| --- | --- |
| H1. Owner receipt during action execution | Eligible repeated intent is retained as belonging to the active episode and subsumed. No second action invocation. |
| H2. Runtime-pending during action; first qualified owner receipt after clean settlement | Fresh owner-received request. Apply the applicable fresh delivery rules; do not silently lose it or attach it retroactively to the closed episode. Earlier physical generation is acknowledged, not renamed. |
| H3. Owner receipt after genuinely clean completion | Later independent cancellation remains deliverable under applicable ordinary or later-episode authority. No native wait reopens. |
| H4. Receipt races settlement | One demonstrated ordering respecting completed prior operations determines old versus fresh membership. Retain exactly one classification; no duplicate delivery or lost intent. |
| H5. Intended action exception while another request is pending | The intended exception counts as completion/delivery when accounted for. Already-received eligible intent remains subsumed in that episode. Runtime-pending-only intent is classified at its qualified receipt; it is fresh if first received after clean settlement. No uncertain-action replay. |
| H6. Shutdown with pending/claimed intent | No false clean shutdown. Retain delivery, claimed-invocation and restoration obligations; do not destroy the owner/broker while accepted obligations remain unresolved or assume claimed means delivered. |
| H7. Two action invocations while the first action remains active | Prohibited. Receipt ordering cannot excuse the known failure or turn a still-executing action into a settled episode. |
| H8. Authorized adapter retains the request before settlement; dequeue occurs afterward | Earlier qualified receipt/membership survives. Retention on behalf of the owner participates in the receipt protocol; dequeue cannot manufacture independence. |

H2 presupposes that no qualified owner/participating-adapter receipt occurred earlier.
If an adapter already retained the request before settlement, H8 applies instead.
H4 does not permit ordering contrary to a completed H1 or H8 receipt. H5 does not
declare all exceptions intended cancellation; actual uncertain invocation/completion
retains the adopted failed-state and non-replay requirements.

## 9. Precise mapping to adopted clauses

All references in this table are to the immediate adopted reaper clarification.

| Existing clause | Precise ambiguity or relevant boundary | Proposed definition/resolution | Unchanged obligations |
| --- | --- | --- | --- |
| §8: finite explicit supported sources; interpreter-pending coverage | Runtime pending and owner ingress are not explicitly separated for membership. | Require a source-specific qualified ingress; pending indication alone does not establish membership unless the source contract makes it owner receipt. | Required SIGINT and supported-source coverage, protection/liveness qualification, no arbitrary BaseException retry. |
| §10: requests received while deferred must remain represented | The first authoritative receipt, including adapter retention, is unspecified. | Receipt is first qualified retention under owner authority, classified indivisibly against settlement; later acceptance cannot shift it. | Reachable bounded retention, no loss, no duplicate delivery. |
| §10: first accepted request selects action; repeated requests before/during action are subsumed | Whether earlier physical/runtime occurrence or owner receipt makes a repeated request belong is not explicit. | Active-episode membership follows ordered qualified receipt; earlier participating retention counts. | First-request action selection, same-enclosing-work/no-independent-side-effect eligibility, at most one action per episode. |
| §10: request arriving during delivery is subsumed even if action raises | Delayed callback/receipt after proposed settlement leaves the meaning of arrival unresolved. | Arrival for this membership decision means qualified owner receipt. H1 is subsumed; H2 is fresh; H5 distinguishes retained intent from runtime-pending-only intent. | No reentrant second action, intended exception counts as delivery, no replay of uncertain action. |
| §10: later independent request after clean completion remains deliverable | Independence and the settlement boundary are not defined for the delayed-event history. | Independence follows fresh receipt after genuinely clean settlement, not an assertion about generation time or causality. | Later delivery remains possible; stale clearing prohibited; native wait remains closed. |
| §10: restoration, teardown and explicit failed completion | A membership rule could otherwise be mistaken for sufficient shutdown proof or early settlement permission. | Settlement requires all §7 prerequisites; absence of received requests does not prove runtime quiescence or safe capability release. | Exact restoration, unresolved obligations retained, no healthy reuse, no caller-visible live context. |
| §12: acquisition-F2 relationship | Reaper receipt might be inferred from acquisition implementation or broadened into it. | This supplement defines only the delayed-request reaper interpretation; no new acquisition semantic or machinery is imported. | Acquisition F2 scope, actor separation, no generic protected waits or retirement-as-child-cleanup fallback. |

If separately adopted and Git-effective, this supplement supplies only these receipt,
arrival, independence and settlement interpretations. It does not claim the original
clarification already expressed this policy choice. The adopted document remains
byte-exact. All unrelated requirements continue; contradictions block adoption or
implementation rather than authorizing silent reinterpretation.

## 10. Source lifetime, restoration, failure and shutdown limits

The owner-receipt definition MUST NOT be used to remove required SIGINT coverage,
drop supported runtime-pending delivery, ignore a source that defeats an implementation,
allow healthy reuse after unresolved restoration/delivery, replay an uncertain action,
or destroy a broker/owner while its accepted obligations remain unresolved.
Here broker is only a description of a possible mechanism, not adopted architecture.

No owner-received intent is not the same fact as no OS/runtime event. Earlier pending
events still require coverage through the applicable ordinary/source-lifetime rules
when received. Restoration and owner shutdown must not remove that coverage between
episode settlement and delayed delivery. Received obligations must stay discoverable;
this document creates no new ownership-transfer or successor-broker authority.

Receipt ordering alone does not solve final capability release, shutdown races,
runtime-pending delivery coverage, handler replacement, actor ownership or unsupported
execution conditions. Those whole-lifetime qualification duties remain. A candidate
mechanism unable to establish safe source lifetime or final executable shutdown stays
blocked. It cannot solve that failure by silently narrowing retention obligations,
pretending a runtime event does not exist, or absorbing future requests forever.

Actual process death still carries no Python continuation guarantee. Parent retirement
is not child cleanup. The supplement grants no new exit, signal, timeout, pre-gate
abort, native wait or destructive recovery authority. Unresolved delivery/restoration
continues to select existing explicit failure rather than fictional clean completion.

## 11. Implementation consequences and required future evidence

The consequences are source-specific qualified receipt, membership retained before
later processing, demonstrated receipt/settlement ordering, action completion before
clean settlement, no discretionary acceptance delay and unchanged whole-lifetime
coverage. No source-generation timestamp is required merely to classify H2. Harness
timestamps or episode labels MUST NOT substitute for production ingress authority.
There is no claim that these requirements already have a qualified implementation.

After separate authorization, evidence must cover:

- H1–H8 separately, including delayed runtime delivery and adapter retention before
  settlement with processing afterward.
- Callback, qualified receipt and actual action-invocation/completion counters as
  separate observations; one callback is not automatically one action or one native wait.
- Same-thread callback/action reentry and concurrent receipts at settlement boundaries,
  including completed-before and overlapping operations with demonstrated ordering.
- Intended cancellation exceptions, uncertain invocation/completion, restoration and
  delivery failures, retained membership and prohibition on automatic action replay.
- One request, eligible repeated requests, later independent cancellation after clean
  completion and rejection of premature settlement while an action remains active.
- Unchanged acquisition-policy composition and actor/source eligibility, including
  preserved required SIGINT and runtime-pending coverage.
- Final executable shutdown with pending, claimed, delivered and subsumed intent;
  source/capability lifetime, handler replacement/restoration and failure exclusions
  across the entire lifetime, not only an isolated episode-state helper.

Use assertions before harness cleanup and GC-disabled observation where useful.
Distinguish synthetic scheduling, callback/receipt/action counts and actual qualified
runtime behavior. Record the exact environment and its limits. Do not infer host
acceptance from an isolated experiment or fabricate totals from overlapping selections.

This draft authorizes no broker, signal, native-spawn or child experiment and no
production/test/configuration edit. Verification performed for drafting is confined
to non-mutating identity, authority and repository checks plus review of this one
new document. Implementation suites are not represented as new evidence for receipt
semantics, and no proposed mechanism is approved by this specification.

## 12. Unchanged authority, unresolved blockers and non-goals

The supplement does not revise exclusive same-handle admission, contender rejection,
continuous reaping responsibility, the one governed `os.waitpid(wrapper_pid, 0)`
operation, InterruptedError-only retry, ECHILD/second-reap process-instance mismatch,
terminal evidence, exact required restoration, at-most-once action per episode,
existing eligibility/subsumption conditions or later independent cancellation.
Fresh cancellation never creates native-wait permission for a terminal handle.
Statuses 10, 12 and 70 and all public error meanings remain unchanged.

Acquisition F2 does not automatically govern reaping, and this document does not
change acquisition-policy composition. There is no general signal-deferral policy,
arbitrary protected blocking syscall, general locking design, multiple waiter,
process-supervision redesign, worker IPC change, broad spawn-lifetime rule,
descriptor ownership change or reservation/accounting change.

This candidate does not approve the executable-owned broker, rejected `_wait_consumed`
primitive, any native spawn adapter, pre-gate abort or new signaling permission,
production actor attachment, Slice 4, governed-host acceptance or numeric-envelope
adoption. Spawn-result ownership and authenticated cleanup progress remain separate
unresolved blockers; receipt/settlement policy does not settle them.

No readiness/Experiment-005 execution, provider/outcome authority, production adapter,
wallet/funding, transaction construction/signing/submission, capital allocation,
real-SOL activity or production mining is authorized. Numeric mode remains
`BOUNDED_STREAMING_MEASUREMENT_CANDIDATE`. No checkpoint is created or edited.

## 13. Review, adoption and implementation sequencing

Required sequence:

```text
candidate draft
  -> independent exact-byte governance review
  -> explicit separate adoption and Git effectiveness
  -> separately authorized settlement experiment
  -> subsequent capability/correction decisions based on evidence
```

Drafting or review alone changes no adopted authority and authorizes no code.
Adoption/Git effectiveness requires its own explicit authorization and authenticated
reviewed content, repository state, bounded commit/publication and independent live
remote verification under the applicable adoption convention. This document performs
none of those steps. Its candidate wording does not purport to adopt itself.

The adopted reaper clarification's correction/validation/independent re-freeze gates
remain in force. A settlement experiment, if later authorized, is not primitive
correction approval or re-freeze. Subsequent capability and correction decisions
must address their own remaining blockers. Primitive correction and Slice-4 review
remain paused; no automatic continuation follows a draft or review pass.

## 14. One-file preservation and final identity

The sole authorized new path is
`docs/research/governance/rq003-stage3c-sole-reaper-cancellation-receipt-settlement-clarification-candidate.md`.
Its absence from worktree, index and HEAD was verified before creation. No unexpected
existing file may be overwritten and no other repository path may change.

After drafting, require all 697 pre-existing path identities/types/modes and relevant
Git classifications unchanged, including both paused implementation identities,
the eight adopted governance documents, checkpoint, required prior authority and
unrelated work. The post-draft population must be exactly 698 unique preservation
paths, with 5 tracked modifications + 28 untracked = 33. Index stays empty; local,
tracking and independently queried live remote HEAD stay at the authenticated
baseline, divergence remains 0/0 and `git diff --check` passes. The new untracked
file also requires its own whitespace/encoding check.

No ignored operational storage or live process is accessed to stabilize this
inventory. Unexpected concurrent repository change is a stop condition, not cleanup
permission. Final byte count, line count and SHA-256 are reported externally; no
self-hash fixed point is embedded. No staging, commit, push, fetch, reference change,
settlement experiment, implementation or Slice-4 resumption occurs in this task.

**SUPPLEMENTARY CANDIDATE ONLY — NO NEW AUTHORITY ADOPTED; PRIMITIVE CORRECTION AND
SLICE-4 REMAIN PAUSED.**
