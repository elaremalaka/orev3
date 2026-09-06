# Stage 3C admission serialization and commit finality adopted clarification

## 1. Status, authority and scope

**ADOPTED CLARIFICATION — GIT EFFECTIVENESS PENDING — NO IMPLEMENTATION AUTHORITY.**

Following exact-byte independent review and explicit user authorization, this
status edit adopts the reviewed clarification. MUST/MUST NOT statements below
become effective only after a separately authorized one-path commit, normal push
and independent live-remote verification under §10. Upon effectiveness, this
supplements only controller admission serialization and commit finality under
controlling §§9/9.1. Unrelated authority remains controlling. Adoption alone
provides neither Git effectiveness nor Slice-3 correction/implementation authority.

Exact governing documents:

- `docs/research/governance/rq003-experiment-005-bounded-streaming-source-processing-prerequisite-v1.md`
  ([controlling governance](rq003-experiment-005-bounded-streaming-source-processing-prerequisite-v1.md)),
  SHA-256 `ce09153fc98145f3fa318a9c7e8dd563afbf4b64496e64535b27c49c93af90e3`.
- `docs/research/governance/rq003-stage3c-recovery-permission-clarification-candidate.md`
  ([Git-effective recovery clarification](rq003-stage3c-recovery-permission-clarification-candidate.md)),
  SHA-256 `7df413610a54adcacb06f5c01dc43b7ce2c04c5244922519871d745c0395f716`.
- `docs/research/governance/rq003-stage3c-category-attribution-clarification-candidate.md`
  ([Git-effective category clarification](rq003-stage3c-category-attribution-clarification-candidate.md)),
  SHA-256 `2e735f2ffe1b4d537495dd7db62d75e21bb6db822c20863f5dc29781c508c101`.

Authenticated source anchor: `95295a8bd074d803e9405a533915b5592a484ae7`.
The goal remains an ORE miner eventually trustworthy with real SOL. This document
addresses one admission blocker, not general threading or filesystem security.

## 2. Gap and decision rationale

Controlling §9 requires coordination locking and complete logical accounting;
§9.1 requires descriptor-derived category observations, ACK-only commitment,
reserve-before-growth and conservative failure retention. The adopted category
clarification fixes roles and requires complete category inventories. None alone
excludes authorized same-process mutation between the final sample and commit.

The current runtime's synchronous reservation reentry guard explicitly is not a
thread lock. Accounting borrows creator-owned descriptors. Repeated inventory can
detect earlier changes but leaves a final interval. Model-B import-session thread
census is not a controller-wide accounting serialization guarantee. These are
implementation compatibility observations, not additional governing authority.

| Option | Assessment |
| --- | --- |
| Single synchronous transition owner, coordination flock and writer quiescence | Selected: constrains authorized execution and preserves existing processes/protocol; no general threading framework |
| Shared intra-controller lock across all authorized mutators | Valid implementation of the same ownership rule where actual concurrent callers exist; a lock on accounting alone is insufficient |
| Repeat sampling without exclusion | Rejected as sufficient authority: mutation can occur after the last sample |
| Descriptor duplication without exclusion | Rejected as sufficient authority: pins another reference but does not freeze inode length or namespace/bindings |

The selected rule is logical single ownership, not a claim that Python execution
or the GIL supplies atomicity. Supporting locks/checks may implement that rule.

## 3. Trust and ownership contract

The controller is the trusted accounting authority. This protocol does not attempt
to survive arbitrary malicious code executing with equivalent controller privileges.
Deliberate trusted-code bypass of this contract is outside the governed internal
threat model. Authorized creators, writers, callbacks, handlers and concurrent
callers MUST obey the contract; the exclusion cannot excuse their mutation.

One controller transition owner MUST exclusively control admission-relevant state
through each authoritative interval. Synchronous execution suffices only where all
authorized paths actually obey that ownership. Actual concurrent authorized callers
MUST share an exclusion mechanism covering every such mutator. Per-object boolean
reentry flags alone are not evidence of concurrent exclusion. Nested admission or
mutation attempts reject under the existing reentry rules, never silently proceed.

Acquisition order is controller transition ownership first, then the required
coordination flock. Release order is coordination authority, then controller
ownership, after the decision and authority-dependent work. All participating paths
MUST use this order; they MUST NOT acquire controller ownership while already holding
coordination authority through a conflicting path. The transition owner covers the
controller's relevant namespace/operation owners, not merely one reservation method.
The flock serializes cooperating controller instances; local ownership serializes
authorized intra-controller execution. Neither replaces the operation lease.

## 4. Mutation and borrowed-descriptor exclusion

From authentication through decision commitment, no other authorized path may change
sampled payload lengths, object membership, namespace names, category/role bindings,
operation authority or reservation ledger/sequence. This covers creation, growth,
truncation, publication/copy, rename/unlink, cleanup/recovery and operation teardown.
Required mode/UID/type/link/identity predicates must remain valid. Previously
acknowledged growth before the interval is permitted only subject to reconciliation;
it is not permission for unincorporated mutation inside the interval.

Accounting continues to BORROW descriptors. It does not become another disposal
owner. The owning controller context MUST prevent relevant borrowed FD close,
replacement, transfer or dup2 substitution during the interval. Authorized duplicate/
alias operations that could undermine exclusion must also be serialized. Observation
scratch descriptors retain the existing single disposal owner. Duplication may aid
identity checking but cannot substitute for length/namespace mutation exclusion.

Read-only work is permitted only if it cannot invalidate authority. Observation/read
callbacks MUST be read-only with respect to admission-relevant state and MUST NOT
initiate another such mutation. Existing synchronous reentry rejection remains.
An authorized signal/asynchronous handler MUST defer admission-relevant mutation
until ownership is available; it must not recursively acquire ownership or mutate
through a bypass. This does not globally disable Python signals. If exclusion cannot
be established or is lost, fail closed without issuing a new ACK.

## 5. Worker quiescence

New requested growth is unavailable until its matching ACK. Complete admission also
requires quiescence with respect to EARLIER allowances for all sampled objects.

A participating governed writer MUST finish/stop its current write before entering
the synchronous request-and-wait phase, and MUST perform no writes, including spending
old allowance, while that request awaits the decision. The controller MUST establish
this state from its trusted writer/launcher execution contract and owned request
lifecycle, not from an added worker boolean, pathname, or unverified claim. Every
other writer to the sampled objects must either be inactive under controller-owned
lifecycle authority or participate in equivalent exclusion. Controller capture/copy
writers are covered by local transition ownership. Earlier unused allowances remain
reserved until existing reconciliation permits release; quiescence alone releases
nothing. An outstanding grant without established writer quiescence is insufficient
for a new authoritative admission interval: defer admission or fail closed.

This is a sequencing obligation on the existing synchronous governed writer, not a
new wire message, listener, process, pause command or worker access to controller FD
tables. If an actual integration cannot establish it using existing writer authority,
that integration remains blocked; this document does not silently authorize a new
worker protocol. Capability/Seatbelt enforcement remains governed-host evidence;
synthetic request sequencing does not prove host acceptance.

## 6. Authoritative admission interval

While holding both forms of authority and established writer quiescence, the owner
MUST perform this sequence:

1. Authenticate operation/lease/confinement authority, all relevant descriptors,
   namespace membership and fixed category bindings.
2. Sample complete observations for all five categories, including every retained
   charge-bearing object, with existing checked arithmetic.
3. Validate ALL observations against established accounting and acknowledged
   allowances. Every retained byte must be explained. Unexplained growth in any
   category rejects; validating only the requested category is insufficient.
4. Validate the requested category, sequence, current size, prospective growth and
   total budget under existing rules. Preserve outstanding/uncertain floors.
5. Construct the complete prospective state and ACK, or rejection, without exposing
   accepted capacity or advancing sequence.
6. Commit one complete logical result, or terminate/reject under existing rules.
7. Complete authority-dependent work, then release exclusion in the stated order.

The first ACK has no exemption. A new observation MUST NOT silently initialize or
rebase the ledger to legitimize unexplained growth. Existing authenticated initial
accounting must itself precede and explain the growth being admitted; this rule does
not remove the already-governed initial accounting of authenticated retained objects.

Illustrative test case, not a numeric policy: budget 10, unexplained reconstruction
growth 5, and requested controller-temporary growth 10 MUST reject before ACK or
sequence commitment because the reconstruction growth is unexplained.

Separate prepare/issue APIs may remain. A prepared snapshot that outlives exclusion
is provisional only. Either retain uninterrupted authority through commit, or perform
fresh COMPLETE validation during issuance under a new authoritative interval. Mere
comparison with an old sample, or repeated sampling without exclusion, is insufficient.

## 7. Commit, interruption and failure finality

Successful admission has one logical commit point: publication of the complete
validated charged/reserved/sequence state together with its matching ACK authority.
Preparing or constructing ACK bytes is not commitment. No accepted reservation,
sequence advance or spendable capacity may escape before that point. Protocol/state/
resource rejection preserves existing terminal-rejection behavior without changing
accepted ledger values or sequence. The clarification adds no rejection code or wire field.

Implementation MUST prevent observers, handlers and exception recovery from seeing
or using partially published logical state. It must establish an all-before or
all-after result at the commit boundary, including KeyboardInterrupt/SystemExit.
A series of assignments plus an outer catch is not by itself proof. Suitable bounded
implementation may stage an immutable result and publish through one authoritative
state boundary, with interruption handling preserving the committed result. No
persistent transaction journal or rollback-after-commit protocol is introduced.

| Failure point | Required disposition |
| --- | --- |
| Observation failure or accounting mismatch | No new accepted reservation/sequence; invalidate observation and fail closed under existing rejection/failure rules |
| Protocol rejection | Existing terminal rejection; no accepted accounting/sequence mutation |
| Callback exception, including BaseException | Before commit, no partial acceptance; invalidate provisional result and terminate/quarantine as applicable; preserve prior floors |
| KeyboardInterrupt/SystemExit before commit | Same pre-commit rule; cannot leave provisional capacity usable; propagate/terminate only with ownership cleanup or quarantine |
| Interruption at commit | Establish complete pre-commit or complete post-commit state; never a usable partial ledger/sequence result |
| ACK construction failure | Pre-commit failure; no new capacity or sequence advancement |
| ACK committed but delivery fails/is uncertain | Preserve committed accounting and existing conservative uncertain-growth rules; do not roll back the grant |
| Post-commit scratch teardown failure | Error/quarantine and block subsequent use as required; do not retroactively undo proven accounting |

Guards/ownership must be relinquished safely on exceptional exit. Inability to prove
resource disposal or ownership restoration quarantines the affected owner; it must
not permit reuse of an uncertain FD integer or further admission. Known post-commit
resource failure is not converted into a fictional pre-commit rejection. This finality
rule does not weaken payload uncertainty: uncertain writes retain existing floors.

## 8. Orderly reconciliation

Verified orderly completion uses the same exclusion, complete authenticated
observation and logical-publication discipline. All reconciliation proofs must pass
before any capacity is released. Bare EOF remains insufficient orderly authority.

Illustration, not a new limit: acknowledged capacity 10, verified orderly completion,
authenticated actual length 3, then committed reconciliation to 3 releases the seven
unwritten bytes. A later observation-scratch close failure does NOT restore 10.
The bridge may quarantine/error and block later use, but the reconciliation is final.
If authority or observation failed BEFORE commitment, release was not proven and
existing conservative retention applies. Scratch lifetime is not payload authority.

## 9. Adversarial checks and implementation scope

| Case | Disposition |
| --- | --- |
| Unexplained growth before first ACK | Reject without ledger rebaselining or sequence advance |
| Unexplained growth in another category | Reject on complete validation before ACK |
| Authorized controller write during sampling | Must be excluded by transition ownership; attempted bypass invalidates admission |
| Callback write or dup2 | Prohibited authorized behavior; reject/quarantine if attempted/detected; no claim of surviving arbitrary controller compromise |
| Other controller instance | Coordination flock excludes conflicting coordinated transition; lease/live-root rules remain |
| Worker waiting for ACK | No new or earlier-allowance spending during established request-wait quiescence |
| Worker with earlier allowance | No admission until its sampled-state mutation is quiescent; allowance remains reserved |
| KeyboardInterrupt before commit | No new accepted state; safe exit/quarantine |
| KeyboardInterrupt at boundary | Complete before/after result only; committed grant retained if delivery uncertain |
| ACK construction failure | No commitment |
| Orderly reconciliation then scratch-close failure | Reconciled value remains final; quarantine resource owner |

Expected correction is controller-side within runtime.py and worker-boundary tests;
this document supplies no implementation authorization or claim that current code
already complies. Existing reentry guards may be retained, but must compose with
whole-interval ownership. Tests must cover complete first/subsequent observations,
all authorized mutation routes, prepare/issue separation, borrowed-FD lifetime,
pre/post-commit BaseException injection, uncertain delivery and reconciliation
finality. No probes or implementation tests are run by creating this document.

No new production component is logically required for the synchronous model. Actual
writer integration must demonstrate quiescence through the existing contract; inability
to do so must be reported as a boundary blocker, not solved by an unapproved protocol.
No general threading framework, persistent transaction journal, new process, numeric
limit, category transfer, sixth category, or recovery redesign is introduced.

## 10. Adoption record, effectiveness and non-authorizations

The independently reviewed candidate identity was:

- Path: `docs/research/governance/rq003-stage3c-admission-serialization-clarification-candidate.md`
- Bytes: 16918; lines: 248
- SHA-256: `d7a6fd0fffcbd29186dd3b9b01fc291aee676cb368fdb7362dccccbe8aa71499`
- Review disposition: **STAGE 3C ADMISSION-SERIALIZATION CANDIDATE REVIEW PASSED —
  EXPLICIT ADOPTION MAY BE CONSIDERED**

That independent review authenticated exact bytes and all three governing identities,
checked mutation coverage, writer quiescence and commit/failure finality, and confirmed
compatibility with fixed categories, recovery and frozen boundaries. Subsequent
explicit user authorization permits this status/authority edit only; the reviewed
serialization/accounting/finality semantics remain unchanged.

Document status is ADOPTED CLARIFICATION; Git effectiveness remains pending.
Consistent with established repository practice, effectiveness requires a separately
authorized commit containing only this path, normal push to the configured tracking
branch, and independent live-remote verification. This edit performs none of those
Git actions and creates no new remote-backed continuation anchor.

Before effectiveness, independently authenticate the adopted bytes and status-only
diff, all three governing identities, frozen Slice-3 identities, checkpoint/RFC
identities, repository/Git authority, index and reconciled mutable/write boundary.
Report the exact adopted byte count and SHA-256 externally; no self-hash fixed point
is embedded. Adoption, commit, push, independent remote verification and implementation
authorization remain distinct transitions. Slice-3 correction/implementation requires
Git effectiveness and independent authentication of the adopted identity, followed
by separate explicit authorization bound to that authority.
No comprehensive checkpoint is created by this clarification.

No Slice-3 implementation, writer/IPC activation, publication/dedup implementation,
RSS/watchdog, numeric adoption, governed-host acceptance, readiness candidate/evidence/
E/R, Experiment-005, provider/backend/outcome, production/Paper Miner, wallet,
transaction construction/signing/submission, capital allocation or real SOL activity
is authorized. Numeric mode remains `BOUNDED_STREAMING_MEASUREMENT_CANDIDATE`.
