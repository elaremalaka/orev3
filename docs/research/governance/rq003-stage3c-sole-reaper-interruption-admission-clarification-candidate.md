# Stage 3C Sole-Reaper Interruption and Same-Handle Admission Clarification

**GOVERNANCE CLARIFICATION CANDIDATE — INDEPENDENT REVIEW REQUIRED — NOT ADOPTED — NOT GIT-EFFECTIVE — NO IMPLEMENTATION AUTHORITY**

Drafted 2026-09-08 under authorization to create this document only.

## 1. Status, purpose and authority bindings

This candidate answers only:

> How must the existing sole reaper establish one exclusive, continuously owned
> wait operation and preserve its obligation and terminal evidence across
> supported asynchronous interruption, without relying on exact kernel-entry
> acknowledgment, permitting another waiter, retrying anything except
> InterruptedError, treating ECHILD as successful reaping, losing the obligation
> before native waiting, or broadening process-supervision/cancellation policy?

MUST/MUST NOT statements below are proposed normative requirements. They do not
change adopted authority until independent review, explicit adoption and separately
authorized Git effectiveness. Drafting neither authorizes primitive correction nor
freezes the current primitive candidate or Slice 4. It authorizes no Git operation.
The objective remains an ORE miner eventually trustworthy with real SOL; this
candidate grants no operational or real-capital authority.

The following seven controlling documents were read during the preceding assessment
and independently reauthenticated before this draft. Paths are relative to
`docs/research/governance/`. Every working file equals its committed HEAD blob;
all listed commits are ancestors of the independently verified live remote HEAD.

| Authority / exact filename | Bytes | SHA-256 | Document commit |
| --- | ---: | --- | --- |
| `rq003-experiment-005-bounded-streaming-source-processing-prerequisite-v1.md` | 179582 | `ce09153fc98145f3fa318a9c7e8dd563afbf4b64496e64535b27c49c93af90e3` | `a46173a0420d0bfd4babd17cd1ebbaa911bce241` |
| `rq003-stage3c-recovery-permission-clarification-candidate.md` | 47955 | `7df413610a54adcacb06f5c01dc43b7ce2c04c5244922519871d745c0395f716` | `045c041453d232e1288e6031fc528d61f8989caa` |
| `rq003-stage3c-category-attribution-clarification-candidate.md` | 19936 | `2e735f2ffe1b4d537495dd7db62d75e21bb6db822c20863f5dc29781c508c101` | `95295a8bd074d803e9405a533915b5592a484ae7` |
| `rq003-stage3c-admission-serialization-clarification-candidate.md` | 18602 | `56b4e402a9b4e62853e285be3ed7ca7b7c2d1a0d34d71a7c9ee757b8dffdcfed` | `a7f0ea131237fd6f073f14a3d2fc8544920e6aba` |
| `rq003-stage3c-acquisition-lifetime-clarification-candidate.md` | 30330 | `1e2c235f11689cd64c65840b3055f377ebef8d9614ea31574e398a15bf29fdcd` | `fcc2f3f42c94c691b65012fab9d0c75bebc4ef94` |
| `rq003-stage3c-controller-retirement-status-clarification-candidate.md` | 18484 | `d9bf01b2449b1819545ef4c186407eb0c16c929534d6ff4bc2f37b8a4b33a304` | `d14b516277441a3849525014a92c09529347eadb` |
| `rq003-stage3c-worker-pinned-input-acquisition-lifetime-clarification-candidate.md` | 24156 | `be25dd7422e10c6dc775bb3fabbfc0688c71606fdaf8196305f1282208628a9c` | `90018eeb54cb1e8590f526f72579ba262dd868d4` |

The [controlling prerequisite](rq003-experiment-005-bounded-streaming-source-processing-prerequisite-v1.md)
§10.1, particularly its final-reaping provisions at lines 1738–1760 and sole-owner
status-70 provisions at lines 1312–1318, remains authoritative. Its §16 requires
competing/double-reaper rejection and zombie evidence. This candidate supplements
only exclusive admission, supported interruption and terminal evidence for that
operation. Unrelated authority is not superseded; a substantive conflict blocks
adoption rather than granting automatic precedence to this candidate.

## 2. Authenticated starting repository and preservation boundary

| Property | Independently verified before drafting |
| --- | --- |
| Repository | `/Users/erale/Documents/orev3` |
| Branch / upstream | `research/post-v1` / `origin/research/post-v1` |
| Local / tracking / live remote HEAD | `ad92eeab8ca0000509069a170369f7ecd20a14f9` |
| Parent | `ff36b9a1a1afd1814f0e676565ae4d3fb49b7f93` |
| Ahead / behind | 0 / 0 |
| Index | Empty |
| Mutable population | 5 tracked modifications + 27 untracked = 32 |
| Pre-existing inventory | 696 unique tracked/nonignored-untracked file paths |
| `git diff --check` | Pass |

Live authority was queried with read-only `git ls-remote`, independently of the
tracking ref. HEAD records the 28-path frozen Stage-3C implementation candidate.
The preceding checkpoint was committed separately at its parent above.

Checkpoint path:
`docs/project-checkpoints/ore-v3-stage3c-cross-layer-frozen-comprehensive-continuation-candidate.md`.
Identity: 133128 bytes, SHA-256
`9074543bb4c5b64576f01897c55b1945a163ce532e1b940ed4f140ab0f227a90`;
working bytes equal HEAD. Its historical uncommitted/pending prose describes its
drafting time, not the subsequent promoted implementation baseline.

All 695 checkpoint Appendix-A identities were reconciled. Current working bytes
match 693; the two exceptions below match the appendix when read from HEAD and
match the separately authorized paused combined identities in the working tree.
Thus neither current combined file is mislabeled as the original frozen bytes.

| Paused combined path | Bytes | SHA-256 |
| --- | ---: | --- |
| `src/orev3/execution/runtime.py` | 170595 | `ff833dbd187c65456c3ac1d54a2ab2da19451906f5593184ea0bcddb7e610359` |
| `tests/execution/test_phase3b_worker_boundaries.py` | 305261 | `00d0801b0fc516df35fb99cab1b67ffce5c6f13b42cd30de523c103b07189a30` |

The other three tracked modifications are RFC-007, RFC-008 and the research backlog;
all 27 pre-existing untracked research documents remain unrelated preserved work.
The full starting inventory matched the preceding assessment's manifest digest
`4ee5b09f5c2d59c19e199eb5398e46c8bcba7bd61d5f6a572419f05dec1afcae`.
That digest is SHA-256 of Python `json.dumps(mapping, sort_keys=True).encode()`
for the repository-relative-path to file-SHA-256 mapping, not a new project identity
domain. Exact final draft identity and preservation results are reported externally
to avoid a self-hash fixed point.

## 3. Historical defect record and decision rationale

The preceding independent read-only assessment authenticated these distinct stages:

| Stage | Evidence and limitation |
| --- | --- |
| Frozen latent defect | HEAD's `GovernedSpawnHandle.wait()` retained `_reaped` only after wait returned. ECHILD mapped to canonical mismatch without retaining terminal native finality; a later call could invoke wait again. Other non-retryable native failures also escaped without consuming finality. This existed independently of Slice 4. |
| Round-1 correction | The current uncommitted `_wait_consumed` assignment before the native loop closes repeated ECHILD/native-error waits. This is a failed correction candidate, not newly adopted or frozen authority. |
| Correction-induced defect | Interruption after consumption but before invoking wait leaves zero waits, consumed permission and rejected later cleanup. In-memory probes reproduced KeyboardInterrupt, SystemExit and BaseException. |
| Round-2 analysis | Same-handle reentry/concurrency is not already excluded. Controlled reentry and synchronized concurrent callers after the guard reached the synthetic wait boundary twice. No Round-2 correction was implemented. |
| Governance conclusion | Exact kernel-entry timing cannot be the Python authority boundary. Exclusive continuous operation responsibility and retained terminal evidence must replace permission-only reasoning. |

The assessment compiled unchanged method AST from HEAD/current bytes into isolated
in-memory probes with synthetic wait targets. Those probes prove Python control
flow, not exact kernel entry or governed-host acceptance. Historical test selections
overlap and are not aggregated into a new total. Drafting this document reruns no
primitive validation and does not claim any failed candidate passed re-freeze.

Transition-only deferral is insufficient: interruption during wait or after native
return can still lose responsibility/evidence. Persistent state alone is insufficient
if the executor disappears and only an ownerless active flag survives. A global
single-actor redesign is neither already proved nor necessary authority for this
narrow scope. The proposed rule therefore combines exclusive retained operation
authority with reaper-specific supported-cancellation exclusion through terminal
recording and controlled restoration/delivery. This is a semantic decision, not a
choice of the easiest lock or flag implementation.

## 4. Fixed authority and exact actor applicability

Exactly one authorized reaper authority MUST own the governed measurement-wrapper
PID in the existing `GovernedSpawnHandle`. No second owner, competing waiter or
replacement handle for the same governed invocation is permitted. The existing
final operation remains `os.waitpid(wrapper_pid, 0)`, after clean completion or
authenticated safe termination. Monitoring, process-instance authentication,
unreaped wrapper retention and safe group-signaling prerequisites remain unchanged.
Admission alone MUST NOT authorize early wait or a new termination decision.

The actor is the existing supervising controller that owns the direct spawned
measurement-wrapper handle. Under the already-governed analogous outer topology,
the readiness supervisor owns its directly spawned controller-wrapper handle; the
same rule applies to that handle only. The inner controller continues to own its
own worker-wrapper handle. These are distinct governed handles, not shared reaper
authority. The existing active-worker-first termination ordering remains intact.

No worker gains reaping authority over its wrapper or another process. Actor identity
MUST derive from the authenticated topology and ownership, never filenames, process
names, ambient configuration or stack inspection. In particular, the detached
evidence controller is a controller despite its `evidence_preparation_worker.py`
filename. This rule does not cover unrelated Git/tool children, arbitrary subprocesses,
or the measurement wrapper's own internal wait for its child.

The single-thread MODEL-B input-projector import session is not controller-wide
same-handle exclusion. A single source call site, one worker invocation at a time,
or the GIL is not proof of exclusive reaper entry. Accounting admission ownership
does not automatically cover this wait, and its contender-driven invalidation rule
MUST NOT be copied in a way that abandons an admitted reaper.

## 5. Exclusive admission and continuous responsibility

The proposed logical progression is:

```text
unadmitted outstanding reaping obligation
  -> exactly one caller obtains exclusive reaper-operation admission
  -> that admitted operation continuously owns completion responsibility
  -> terminal evidence/disposition becomes authoritative
  -> native-wait admission closes permanently
```

These are descriptive states, not required public enums or a prescribed data layout.
Terminal publication and permanent closure MUST be one logical finality boundary:
there is no interval in which a terminal outcome permits another admission.

The existing handle and reachable cleanup authority MUST preserve the outstanding
obligation before admission. Supported interruption of admission establishment MUST
leave a complete before/after result: either no admission was consumed and the
outstanding obligation remains executable under its existing owner, or one admitted
operation owns execution through terminal disposition. A caller-local intention,
partially published owner, or later return assignment is insufficient.

Admission MUST be authoritative before interruptible reaper work begins. Exactly
one caller may hold active admission. Protection readiness and responsibility for
its own establishment/teardown MUST exist before enabling an admitted operation;
failure to establish them MUST NOT consume the obligation as if wait had occurred.

Admission is completion responsibility, not a one-use boolean permission. After
admission, the same admitted operation MUST retain an executor and responsibility
through wait and terminal recording. Supported cancellation MUST NOT unwind it and
leave only an active flag. No ownerless active state, GC/finalizer fallback, future
public retry, ownership transfer or replacement waiter supplies completion.

Actual concurrent authorized callers MUST obey one exclusive same-handle admission
boundary. Synchronous paths MUST also exclude reentry. This imposes no general-purpose
locking policy, common launch lock, controller-wide thread prohibition, or lock API.
Implementation must prove the semantic exclusion rather than assume that a sequence
of Python assignments is atomic.

## 6. Contenders, reentry and repeated calls

A concurrent or reentrant competing public `wait()` attempt MUST fail closed as
`RESOURCE_PROCESS_INSTANCE_MISMATCH`, with zero native wait invocations by that
attempt. It MUST NOT revoke, invalidate, reset or abandon the admitted owner's
responsibility. This specializes the controlling competing-reaper rejection; it
introduces no new public code.

The contender MUST NOT join, wait for the admitted caller, obtain cached successful
return, take ownership, or become another waiter. Reentrant waiting on the same
owner is especially not a permitted way to serialize entry. Authorized callbacks
and handlers must obey this restriction. Contender rejection must not escape through
an admitted owner's callback/handler and thereby abort that owner's operation;
the supported execution contract must prevent that route or fail qualification.

After terminal disposition, every later public `wait()` attempt MUST reject under
the existing second-reap/process-instance-mismatch semantics without native wait.
Retained terminal evidence remains available to the existing governing cleanup
authority; this does not create an idempotent successful public wait API. Repeated
cleanup cannot reopen admission or use historical PID/group evidence to authorize
fresh signaling after its existing process authority has ended.

## 7. Native-entry observability and native retry

Correctness MUST NOT depend on Python proving the instant the kernel wait began.
A pre-call flag, entry into a Python wrapper/monkeypatch, tracing/profiling event,
C-wrapper entry, or assumed bookkeeping-to-native atomicity is not such proof.
Likewise an exception class alone cannot decide whether the kernel operation began
or completed before Python received its result. The continuously owned admitted
operation, rather than a guessed entry receipt, supplies authority.

Technical evidence used by the assessment is the version-pinned
[CPython 3.14.5 wait implementation](https://raw.githubusercontent.com/python/cpython/v3.14.5/Modules/posixmodule.c),
`os_waitpid_impl`: it releases the GIL around waitpid, handles EINTR/signals internally,
then constructs the Python result. One Python invocation can therefore contain
runtime-internal EINTR attempts. This is runtime evidence, not an additional retry
policy or permission to replace the governed API.

Only `InterruptedError` permits an application-level retry inside the same admitted
operation. Runtime-internal EINTR handling remains part of that operation; neither
kind of EINTR handling admits another caller. KeyboardInterrupt, SystemExit,
arbitrary BaseException, ECHILD or another non-retryable error MUST NOT become retry
authority. An installed handler must not deliberately manufacture InterruptedError
as cancellation to evade these rules. No polling wait, wait-any-child API, alternative
wait primitive or altered options is introduced.

## 8. Reaper-specific supported interruption model

Supported cancellation consists of cooperative intent to abort the enclosing
governed work, including SIGINT normally translated to KeyboardInterrupt and any
installed raising signal handler admitted by the qualified reaper configuration.
Signal-handler SystemExit or another BaseException has no exemption by class.
Such intent MUST be recorded/deferred, not raised through the admitted operation.
Authorized synchronous code MUST NOT deliberately inject cancellation inside it.
Ordinary synchronous native failures follow §9, not cancellation retry.

The configured supported sources and their delivery actions MUST be finite, explicit
and established before this operation is enabled. A raising handler that cannot
obey this contract makes the environment unsupported for this operation. Deferral
does not retroactively defer an exception already raised. No particular signal
masking/handler API is required; a thread-local mask alone is not proof of coverage
of other threads, interpreter-pending delivery or protection setup/teardown.

| Boundary | Proposed delivery and responsibility rule |
| --- | --- |
| A. Before admission | Immediate supported delivery is permitted only when no admission is consumed and the outstanding cleanup/reaping obligation remains reachable and executable. Caller unwinding must not erase that responsibility. Otherwise delivery must wait for the responsible cleanup path. |
| B. Admitted, before native wait | The admitted owner retains responsibility and proceeds with its one operation. Supported interruption is pending; it cannot unwind the owner or authorize another caller. |
| C. Native wait active | The same admitted operation remains authoritative. Supported cancellation remains pending. Only InterruptedError retries; no arbitrary BaseException retry or substitute waiter. |
| D. Native outcome, before terminal recording | Supported interruption cannot escape before returned PID/raw status or terminal failure evidence and disposition are authoritatively retained. A non-retryable outcome cannot authorize another wait. |
| E. Terminal disposition, before public receipt | Native admission is permanently closed. Terminal evidence survives independently of caller receipt. Delivery follows required restoration/teardown under §10; interruption of final public return cannot erase disposition. |

The narrowly protected purpose includes the existing blocking final wait and its
terminal recording; protection does not stop at presumed native entry. This is an
explicit reaper-specific proposal, not authority to extend acquisition protection.
Bounded purpose is not a universal bound on elapsed wait duration. Integration MUST
establish that existing clean-completion/safe-termination prerequisites and qualified
execution can finish this obligation without relying on a deferred cancellation to
perform work necessary for wait to finish. Failure to prove that liveness composition
blocks integration; no new timeout, watchdog activation or hard-kill authority follows.
Already-authorized hard termination and unavoidable process death are not deferred.

## 9. Authoritative terminal evidence and native finality

Before supported interruption can escape, the existing reachable handle/cleanup
authority MUST retain a complete logical terminal disposition and its supporting
evidence. A disappearing local, transient exception frame, pending caller assignment,
or unreceived return value is insufficient. Evidence must survive subsequent cleanup,
restoration/delivery failures and interrupted public receipt without GC dependence.
No persistent journal, new wire payload or public evidence API is required.

| Native result | Required retained disposition |
| --- | --- |
| Successful attributable reap | Returned PID equals the governed wrapper PID; raw status is retained and accepted only under existing exited/signaled decoding. Retain attributable result and decoded disposition. Native admission closes permanently. |
| ChildProcessError / ECHILD | Retain terminal `RESOURCE_PROCESS_INSTANCE_MISMATCH` and sufficient ECHILD/native-failure classification to distinguish it from attributable success. Do not mark successful reaping. Native admission closes permanently. |
| Other non-retryable native failure | Retain the failure classification/evidence and unsuccessful terminal disposition under existing failure handling. Do not fabricate PID/status or successful reaping. Native admission closes permanently; no bound authority grants another retry. |
| Wrong returned PID | Retain returned PID/raw status and mismatch disposition. No attributable success and no subsequent native wait. |
| Malformed, stopped, continued or unknown status | Retain available returned evidence and existing mismatch disposition. Do not accept status as successful completion; no subsequent native wait. |
| InterruptedError | Nonterminal retry within the same admitted operation only; it is neither success nor a new admission. |

The existing decoder remains limited to `os.WIFEXITED`/`os.WEXITSTATUS` and
`os.WIFSIGNALED`/`os.WTERMSIG`. An exited nonzero value is still an attributable
reap, not successful worker work. Status 70 retains its existing authenticated
integrity meaning; statuses 10 and 12 are not expanded. Native failure evidence
does not allocate a new public error/status or expose raw exception text in closed
diagnostics. Diagnostic emission is never a prerequisite to finality.

Terminal native failure closes retry authority but does NOT prove zombie absence,
child cleanup or attributable reaping. The no-zombie obligation prohibits avoidable
abandonment under supported execution; it is not a license to turn an actual native
failure into success or retry it. A path unable to meet the existing reaping/liveness
requirements remains failed and cannot claim qualification or successful cleanup.

## 10. Pending cancellation, restoration and delivery

The required completion order is:

```text
terminal evidence/disposition authoritative; native admission permanently closed
  -> required protection restoration/teardown completed
  -> pending supported interruption delivered, or explicit failed completion
  -> final public return/raise
```

Protection/restoration authority MUST be reachable before temporary changes occur.
Every original setting that must be restored and every outstanding teardown
obligation must remain discoverable until resolved. Exact restoration must be
verified before clean restoration is declared. Partial restoration cannot appear
healthy, and no caller-visible live protection context may escape.

Supported requests received while delivery is deferred MUST remain represented in
reachable bounded pending state. Representation must distinguish no request, pending
delivery, an exclusively claimed delivery episode, and delivered/subsumed intent;
these are semantic distinctions, not mandated fields. A flag cleared before delivery
actually occurs is not proof of delivery. One request MUST NOT be lost or delivered
twice because of interruption, stale clearing or handler reentry.

This candidate selects one bounded cancellation episode for this final operation.
The first accepted request selects its configured delivery action. Repeated requests
before or during that action are explicitly subsumed by the same episode, provided
all admitted sources mean cancellation of this same enclosing work and require no
independent per-request side effect. The justification is one final cleanup operation
and one cancellation disposition: an unbounded request queue or exact signal count
adds no reaping authority. Sources requiring distinct non-subsumable actions are
outside this model and block qualification rather than being silently dropped.

The first intent MUST stay pending until its action is actually invoked or an
explicit failed completion retains the undelivered obligation. Delivery is eligible
only after terminal evidence and required restoration are complete. The delivery
action MUST execute at most once for the episode; its normal cancellation exception
counts as delivery, not a reason to invoke it again. Reentry during delivery cannot
start another delivery or wait. A request arriving during delivery is subsumed by
the active episode even if its action raises; a later independent request after
clean completion remains deliverable under restored ordinary behavior. The transition
out of the episode must have complete before/after semantics so a stale clear cannot
erase that later request. Implementation must prove these semantics; a pre-action
"delivered" assignment alone is insufficient.

Pending handling MUST occur before normal work resumes. Cancellation does not erase
native failure or turn it into success. Existing native/cleanup failure disposition
must remain discoverable when cancellation supplies the public exceptional exit;
this requirement adds no universal exception-priority policy for unrelated callers.
No successful public completion is permitted while required delivery is unresolved.

Restoration, teardown or delivery-mechanism failure MUST select explicit failed
completion, retain the terminal reaper evidence and all unresolved obligations, and
prevent normal work through the affected protection authority. Native admission
MUST NOT reopen. Undelivered cancellation remains explicitly unresolved; returning
an error is not automatically delivery. No automatic retry of an uncertain handler
invocation, healthy reuse, or status-12 retirement shortcut is authorized. If the
implementation cannot enforce this failed-state exclusion under its supported
execution model, it is not qualified. A configured delivery action raising the
intended cancellation is distinguished from failure to establish/invoke that action.

Restoration itself must remain covered against supported premature raising delivery;
restoring an original handler cannot create a gap before the owned delivery episode
is settled. No protection change may leak to unrelated work as a normal outcome.
Detected incomplete protection is failure, not permission for broad signal deferral.

## 11. Unsupported conditions and limits

Arbitrary tracing/profiling injection, asynchronous exception-injection APIs,
interpreter corruption and unsupported runtime/signal behavior are not authorized
production cancellation mechanisms. Fault tests may exercise these boundaries but
must label them separately from supported real cancellation. An unexpected exception
with an uncertain native outcome must retain discoverable failure/uncertainty where
the runtime permits; it MUST NOT infer non-entry, reset admission, retry a possible
terminal wait or claim successful reap. An active marker without an executor is not
a valid solution to such a breach.

If the environment cannot provide continuous responsibility and retained evidence
under the supported model, that is a qualification/implementation blocker. Retained
uncertainty alone is not evidence that the no-zombie obligation was met. Stronger
native or architectural support would require separate bounded authorization; this
candidate neither mandates nor authorizes a native extension or another actor.

Unavoidable process death provides no Python continuation guarantee. SIGKILL and
SIGSTOP must not be represented as maskable cooperative cancellation. Parent exit,
including controller retirement, does not prove child termination/reaping or release
external references. No new crash recovery, guessed PID, external waiter, destructive
cleanup or orphanhood authority follows from parent death or uncertain wait evidence.

## 12. Acquisition-F2 relationship

Acquisition F2 does NOT automatically govern process reaping. Its bounded acquisition
scope expressly does not authorize arbitrary blocking waits, and its process-local
resource reclamation argument is not child cleanup authority.

This candidate explicitly adopts only these analogous principles for the sole reaper:

1. Responsibility exists before interruptible work.
2. Reachable state/evidence does not depend on caller receipt.
3. Supported cancellation is retained and delivered deterministically.
4. Restoration/teardown has exact, discoverable completion or failure.
5. No caller-visible live protection context is handed out.

The specific episode semantics in §10 are proposed here for this operation; they
are not imported wholesale from F2 implementation. There is no generic `.protected()`
wrapping permission, reuse mandate for acquisition machinery, descriptor-owner
migration or parent-retirement fallback. Controller status 12 remains exclusively
its adopted acquisition-ownership trigger, not wait uncertainty or child cleanup.

## 13. Implementation consequences and minimum forecast

After Git effectiveness and separate implementation authorization, correction must
establish exclusive admission, a continuously responsible executor, retained terminal
evidence, supported interruption exclusion, EINTR-only retry, post-terminal closure,
contender rejection without owner invalidation, and deterministic restoration/delivery.
It must not depend on exact kernel-entry acknowledgment or fabricate success on errors.

Expected production boundary is `src/orev3/execution/runtime.py`, principally
`GovernedSpawnHandle.wait()` and its private state/support, plus narrowly necessary
composition with `BoundedInvocationResources.fail_after_spawn_before_gate()` and
the existing pre-gate cleanup caller. Independent descriptor cleanup failure must
not suppress the admitted reaper obligation. Descriptor ownership, signal target
authentication and reservation/accounting semantics remain fixed.

Expected regression boundary is
`tests/execution/test_phase3b_worker_boundaries.py`. No other production/test file
is demonstrated necessary. No specific boolean, lock, context manager, callback
framework or state class is prescribed. If another trust-bearing path, native
component, actor, closure member or broader lifetime rule proves necessary,
implementation stops for separate authority rather than weakening the contract.

The current paused Slice-4 changes may remain preserved in place. A future correction
must identify its bounded delta separately from those changes and the original
frozen primitive. This draft adopts neither combined file and authorizes no edit.

## 14. Required adversarial validation

Future independent evidence must demonstrate the following, with exact candidate
identities and runtime/signal/thread configuration recorded:

| Area | Required cases and assertions |
| --- | --- |
| Admission | Simultaneous same-handle callers around admission establishment; reentry before/after authoritative admission; one admitted executor only; contenders reject without wait or owner invalidation; repeated sequential calls reject after terminal disposition. |
| Interruption | Before admission; after admission/before call; while real wait blocks; after native outcome/before evidence recording; after terminal recording/before receipt; protection entry, restoration, teardown and delivery. Outstanding or admitted responsibility never disappears under supported cancellation. |
| Native outcomes | Clean exit; signaled exit; EINTR then success; EINTR then ECHILD; ECHILD; other non-retryable native error; wrong PID; malformed/stopped/continued status. Assert exact retry/non-retry behavior, permanent finality and no fabricated success. |
| Cancellation | One supported request; repeated requests under the adopted episode; handler reentry; action raising its intended cancellation; later independent cancellation after clean completion; no lost or duplicate delivery; sources that cannot satisfy subsumption reject qualification. |
| Restoration | Exact original setting restoration; partial/failing restoration; teardown failure; uncertainty before/at action invocation; retained unresolved state; no healthy reuse or public success; terminal evidence and closed native admission survive. |
| Cleanup | Authenticated safe termination, independent descriptor cleanup failures, original cleanup exception context where applicable, sole wait completion/terminal disposition, repeated cleanup with zero additional native wait, no competing reaper, and no zombie for harness-owned children on successful attributable reap paths. |
| Attribution | Correct governed wrapper PID/raw status; nonzero attributable exits distinct from successful work; ECHILD not success; statuses 10/12/70 unchanged; worker and unrelated-process authority not expanded. |

KeyboardInterrupt, SystemExit and BaseException fault injection must be tested at
relevant boundaries without representing all such injections as production-supported
signal delivery. Real SIGINT and other configured raising-handler intent require
separate isolated evidence, including actual blocking wait. No arbitrary exception
may become EINTR retry permission. A monkeypatch entry count is not kernel-entry proof.

Use GC-disabled assertions where useful and assert ownership, terminal evidence,
unresolved obligations and child disposition before harness cleanup. Harness-created
children must have one reaper; a test must not hide production abandonment behind
an independent cleanup waiter or infer ECHILD proves that this owner reaped. Clearly
separate Python-call counts, native/runtime observations, synthetic negative outcomes
and production-shaped governed-host evidence. Test-only scheduling barriers grant no
production synchronization authority. Overlapping selections must not be summed into
a fabricated distinct-test total.

Qualification must cover supported interpreter/version, thread model, signal setup,
pending events, restoration, blocking-wait liveness and the actual actor topology.
The assessment's CPython 3.14.5/macOS evidence is not universal Python atomicity or
governed-host acceptance. Unsupported configurations must reject qualification.
Relevant existing regressions remain required, including `PYTHONPATH=src pytest -q
tests/features`; read-only validation should disable bytecode and pytest cache writes.
No implementation tests are claimed to have run merely because this draft exists.

## 15. Adoption, correction and re-freeze sequencing

Required order:

```text
authorized clarification candidate draft
  -> independent exact-byte governance review
  -> explicitly authorized adoption/status transition
  -> separately authorized bounded commit and normal push
  -> independent adopted-byte/parent/path/live-remote verification: Git-effective
  -> separately authorized bounded primitive correction
  -> focused and adversarial validation
  -> independent primitive re-freeze
  -> only then separately authorized resumption of Slice-4 independent review
```

Independent review and adoption are not implicit commit/push authorization. Before
Git effectiveness, authenticate the final adopted identity, the bounded adoption
diff, committed path and ancestry, index, protected populations and live remote.
Draft/review/adoption identities must be distinguished; no self-hash is embedded.
Implementation receives its own authorization against the effective clarification.

Slice 4 remains paused while the primitive is unresolved. Neither existing selected
regressions nor this document re-freeze a failed correction. Primitive re-freeze is
independent of subsequent Slice-4 review and is not a Stage-3C completion claim.
No comprehensive checkpoint is created, edited or authorized by this clarification.

## 16. Explicit non-goals and draft preservation

This candidate authorizes no general signal deferral, arbitrary protected blocking
syscalls, multiple waiters, general-purpose locking, process-supervision redesign,
worker IPC changes, broad spawn-lifetime redesign, new public status meanings,
descriptor ownership changes, reservation/accounting changes, Slice-4 adoption,
governed-host acceptance or numeric-envelope adoption. It grants no readiness or
Experiment-005 execution, provider/outcome authority, production adapter/registry,
wallet/funding authority, transaction construction/signing/submission, capital
allocation, real-SOL mining or production-mining authority. Numeric mode remains
`BOUNDED_STREAMING_MEASUREMENT_CANDIDATE`.

The authorized drafting write boundary is exactly this new file:
`docs/research/governance/rq003-stage3c-sole-reaper-interruption-admission-clarification-candidate.md`.
All pre-existing 696 inventoried paths, including both paused combined runtime/test
files, seven adopted documents, checkpoint and unrelated work, must remain byte-exact.
Expected post-draft mutable population is 5 tracked modifications + 28 untracked = 33,
with this file the sole added path. The index must remain empty; local/tracking/live
remote HEAD and 0/0 divergence must remain unchanged; `git diff --check` must pass.
No staging, commit, push, primitive correction or Slice-4 resumption occurs here.

**Status remains GOVERNANCE CLARIFICATION CANDIDATE: independent review required,
not adopted, not Git-effective, and no implementation authority.**
