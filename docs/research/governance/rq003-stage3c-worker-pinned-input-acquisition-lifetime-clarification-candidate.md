# Stage 3C affected-worker pinned-input acquisition-lifetime clarification

**ADOPTED CLARIFICATION — GIT EFFECTIVENESS PENDING — NO IMPLEMENTATION AUTHORITY**

## 1. Status, bindings and narrow gap

Following exact-byte independent review and explicit user authorization, this
status edit adopts the reviewed clarification. Creation alone gave it no authority.
MUST/MUST NOT below become Git-effective only after separately authorized one-path
commit, normal push and independent live-remote verification. This edit performs
none of those steps and grants no implementation authority.

Reviewed candidate: 23368 bytes, 329 lines, SHA-256
`baac5611bfcbd15947abc7a3357c36394d2b57aa58308202a004af5f9c998530`.
Independent review disposition:
`STAGE 3C WORKER ACQUISITION-LIFETIME CANDIDATE REVIEW PASSED — EXPLICIT ADOPTION MAY BE CONSIDERED`.
The remote-backed HEAD recorded below remains unchanged by this status edit.

Upon Git effectiveness, this supplements only the affected workers'
pinned read-only input acquisition-lifetime interpretation of controlling §9/§9.1
and worker failure handling. All unrelated requirements remain controlling.

Repository: `/Users/erale/Documents/orev3`; branch `research/post-v1`; tracking
`origin/research/post-v1`. Authenticated local/tracking/live-remote HEAD:
`d14b516277441a3849525014a92c09529347eadb`; parent
`fcc2f3f42c94c691b65012fab9d0c75bebc4ef94`; ahead/behind 0/0.

| Governing authority | Exact repository path | SHA-256 |
| --- | --- | --- |
| Controlling bounded streaming | `docs/research/governance/rq003-experiment-005-bounded-streaming-source-processing-prerequisite-v1.md` | `ce09153fc98145f3fa318a9c7e8dd563afbf4b64496e64535b27c49c93af90e3` |
| Recovery | `docs/research/governance/rq003-stage3c-recovery-permission-clarification-candidate.md` | `7df413610a54adcacb06f5c01dc43b7ce2c04c5244922519871d745c0395f716` |
| Category attribution | `docs/research/governance/rq003-stage3c-category-attribution-clarification-candidate.md` | `2e735f2ffe1b4d537495dd7db62d75e21bb6db822c20863f5dc29781c508c101` |
| Admission serialization | `docs/research/governance/rq003-stage3c-admission-serialization-clarification-candidate.md` | `56b4e402a9b4e62853e285be3ed7ca7b7c2d1a0d34d71a7c9ee757b8dffdcfed` |
| Controller acquisition lifetime | `docs/research/governance/rq003-stage3c-acquisition-lifetime-clarification-candidate.md` | `1e2c235f11689cd64c65840b3055f377ebef8d9614ea31574e398a15bf29fdcd` |
| Controller retirement status | `docs/research/governance/rq003-stage3c-controller-retirement-status-clarification-candidate.md` | `d9bf01b2449b1819545ef4c186407eb0c16c929534d6ff4bc2f37b8a4b33a304` |

Controller acquisition lifetime is Git-effective at
`fcc2f3f42c94c691b65012fab9d0c75bebc4ef94` (30330 bytes / 392 lines).
Controller retirement status is Git-effective at the HEAD above (18484 bytes /
240 lines). Their historical pending-status wording is not changed here.

The gap is the transition from genuinely unprovable worker acquisition ownership
to irreversible unsuccessful termination. Existing authority already rejects
partial results and governs worker death, accounting retention and recovery. It
does not uniquely require that transition for these shared-helper callers.
Neither controller RETIRING/status 12 nor integrity status 70 fills this gap.

## 2. Exact actors and acquisition class

Only the one-shot INPUT_PROJECTOR and REPLAY_PREPARATION actors are covered.
The detached evidence controller in `evidence_preparation_worker.py` is a controller,
despite its filename; it is not covered by this worker rule. No other worker,
long-lived service, publication actor or arbitrary subprocess is included.

Only acquisition of already-existing read-only pinned regular-file inputs through
`open_pinned_regular()` and its non-creating directory traversal is covered.
The source has declared/authenticated input authority; acquisition and descriptor
verification still must authenticate the actual opened object before use. This
does not assume descriptor authentication succeeded before the vulnerable window.

INPUT_PROJECTOR reaches the helper through `project_jsonl()` and
`_verified_regular_file()`. REPLAY_PREPARATION reaches it through both passes in
`load_verified_projection()` and later `VerifiedProjectionStream.__iter__()` reopens.
The rule covers every such acquisition during the invocation, not just startup.

Worker writable/output creation, publication, locks, arbitrary duplication,
pipes, sockets, spawn/PID ownership and future capability acquisition are excluded.
Their occurrence elsewhere in a worker does not bring those acquisitions into this
rule. A new actor or acquisition class requiring this rule blocks integration
pending separate authority; it must not be admitted by analogy.

## 3. Existing transport and no new status decision

Controlling lines 1264–1269 distinguish success 0, ordinary worker statuses 2–11
and dedicated integrity status 70. `input_projection_worker.py:143–163` and
`replay_preparation_worker.py:59–79` use generic exception/rejection status 10.
The bounded bootstrap's outer boundary at lines 936–942 also maps non-SystemExit
BaseException to generic unsuccessful status 10. This is compatibility evidence,
not proof that catchable exception propagation already guarantees terminal exit.

`runtime.py:535–543` classifies authenticated exited status 70 as integrity failure;
other nonzero or signaled results reject as `BOUNDED_WORKER_PROCESS_REJECTED`.
The legacy `run_phase3b_worker()` at lines 3198–3237 rejects nonzero completion
before accepting success JSON. Its generic normalized rejection differs by actor;
none is proof of acquisition cause. Legacy transport is not substituted for the
bounded generation's authenticated process topology and sole-wait-owner rules.

Therefore existing generic unsuccessful worker transport is sufficient to carry
this failed invocation. No new integer, canonical transport identifier, wire enum,
message or decoder branch is needed. In particular, this does NOT define status 10
as acquisition ownership uncertainty. Using the existing generic worker-failure
value for an unsuccessful exit preserves its generic meaning. Other ordinary
validation codes must not be selected arbitrarily as interchangeable failure codes.

The controller needs authenticated unsuccessful termination, not a cause-specific
number. A numeric value alone never authenticates the internal cause. If a future
integration cannot preserve the applicable existing generic failure transport,
it must stop for worker-status authority rather than allocate or reinterpret one.

## 4. Ownership classification and selected interruption model

UNPROVABLE ACQUISITION OWNERSHIP is a descriptive governance condition only:
an in-scope acquisition may have succeeded, but the worker cannot prove whether
each resulting local descriptor entered deterministic cleanup ownership. It is
not a new error enum or protocol identifier.

Before an in-scope acquisition begins, the actor boundary MUST be able to classify
an interrupted exit without needing the missing return value. It must distinguish:

| Classification | Disposition |
| --- | --- |
| Acquisition not attempted, or definitively failed | Existing ordinary worker handling; no invented unknown FD |
| Successful result in deterministic reachable cleanup ownership | Known-owner cleanup and explicit handoff |
| Known descriptor, uncertain close result | Existing non-retry/disposition rules; not earliest acquisition uncertainty |
| Acquisition outcome/initial ownership genuinely unprovable | Irreversible failed invocation and actual unsuccessful termination under §5 |

Selected model: permit supported raising interruption, but terminate unsuccessfully
if it leaves acquisition ownership unprovable. This avoids introducing a worker
signal-deferral subsystem. Real SIGINT/KeyboardInterrupt and any supported installed
raising handler, including signal-handler SystemExit, cannot be ignored as synthetic.
Their disposition follows the classification above. No rule attempts to retroactively
defer a synchronous exception that has already been raised.

Every nested helper acquisition and delayed reopen must remain covered. An inner
catch, translation, finally block or return cannot clear an unresolved classification
or allow an enclosing worker computation to continue. Repeated cancellation cannot
restore success or divert the already-selected terminal route back to useful work.
Ordinary cancellation before acquisition follows existing worker rules.

Tracing/profiling and CPython async-exception injection may test this boundary
adversarially; they gain no new production support. If they produce genuine
unprovable acquisition in a test, the required result is terminal failure, not
controller status 12. Hard process death is separate and is never deferred by this
rule. No signal is selected, watchdog activated or timeout introduced here.

## 5. Irreversible failed invocation and actual exit

Once uncertainty is selected, the affected invocation MUST be irreversibly failed.
It MUST NOT parse inputs, continue reconstruction, create/continue useful output,
report success, initiate another acquisition, or resume request processing. No
catchable exception, flag reset or outer handler may restore useful execution.
This is a one-shot invocation obligation, not the controller's long-lived RETIRING
abstraction and not a new worker service-state protocol.

The actor boundary MUST reach actual unsuccessful worker process termination.
Returning from a helper, emitting rejection JSON, logging, or raising an inner
exception is insufficient. An outer failure boundary is usable only if all paths
after terminal selection preclude useful continuation and reach unsuccessful exit.
The existing `raise SystemExit(10)` snippets alone are not such a proof.

The smallest sufficient mechanism is an actor-owned terminal boundary using the
existing generic unsuccessful worker transport, with a non-returning exit route
where ordinary outer exception propagation cannot guarantee that property. On the
current CPython/POSIX runtime, `os._exit` with the applicable existing generic
worker-failure value is an implementation-compatible route; this changes no numeric
meaning and does not require a dedicated worker exit API or native extension.
It is not a requirement to add a special cause-specific status or to copy controller
`os._exit(12)`. An equivalent proven outer terminal boundary is permissible.

Terminal readiness MUST be established before this rule is enabled. The route must
be available before acquisition; it cannot depend on late imports or new resources.
Logs, rejection payloads, flushing, finalizers, atexit and cleanup are not exit
prerequisites. Potentially blocking or fallible housekeeping must be omitted when
it could prevent exit. Repeated cancellation and caught SystemExit cannot bypass
the terminal route. Ordinary shutdown hooks are not a correctness mechanism.
No local FD guessing, descriptor-table scan/close or retry of uncertain integers is
allowed. Unavoidable hard process death supersedes the route; record actual death.

This guarantee concerns authorized worker execution, including its handlers and
catching paths; it is not immunity to arbitrary hostile code with equivalent
process privilege or a stalled kernel. That limitation cannot excuse authorized
continuation after uncertainty. Optional diagnostics cannot be safety dependencies.

## 6. Known ownership and shared-helper layering

After safe result receipt, ownership must be recorded in a reachable cleanup
authority whose lifetime survives the next helper return/caller assignment.
Helper-to-caller and caller-to-ledger transfer MUST preserve exactly one disposal
authority. A known owner remains responsible until the receiving owner is
authoritative. Avoidable handoff leaks must be corrected, not normalized as terminal
uncertainty. The rule does not rely on GC or finalizers.

Known-owner exceptions retain existing cleanup obligations. Known-owner uncertain
close retains R1: never retry the historical integer, guess its kernel state, or
claim proved release. Existing failure/quarantine/termination handling still applies;
an exception alone does not establish earliest acquisition uncertainty.

| Layer | Responsibility |
| --- | --- |
| Actor-neutral pinned helper | Acquisition/authentication, deterministic known ownership, explicit transfer, known-owner cleanup, uncertain-close non-retry; no process-exit choice |
| Controller boundary | Existing controller acquisition protection, RETIRING and status 12 |
| Affected worker boundary | This clarification's classification/no-continuation/unsuccessful-termination obligation for every in-scope call |
| Caller/ledger | Accept ownership exactly once and dispose/transfer under existing rules |

Actor policy MUST be explicit at a trusted executable/actor boundary or explicitly
passed context. No process-name, environment, stack or filename inference is allowed.
Scientific/shared library functions do not own process-retirement policy.

## 7. Result authority, accounting and reclamation

After terminal selection, buffered stdout, serialized result objects, output-file
appearance, complete bytes or a matching digest cannot become success authority.
The controller MUST observe and authenticate unsuccessful termination under existing
process/wait authority and reject success from that invocation. Artifact verification
remains necessary for successful invocations; it cannot override failed termination.
No semantic resume is introduced.

Actual exit reclaims this worker's process-local descriptor references. For the
in-scope read-only existing input, that requires no input rollback and creates no
output authority. It does not prove which FD existed, that Python cleanup ran,
filesystem cleanup, external-reference disappearance, orphanhood, child death or
recovery success. Cause-specific diagnostics remain non-authoritative unless
separately governed; no persistent acquisition journal is added.

Worker death is not a charge-release event. Existing conservative reservation
floors, no trusted partial output, aggregate orphan reconstruction, lease liveness
and terminal cleanup predicates remain unchanged. Only existing authenticated
reconciliation/removal proof can release charge or authorize deletion.

The safety argument requires the governed topology forbidding worker descendants
and unauthorized external capability copies. It does not infer that parent exit
terminates children. An observed/permitted external copy not accounted for by
existing authority blocks use of this local-reclamation argument. No new child or
spawn lifetime rule is created. Host confinement evidence remains separately required.

| State at worker death | Local effect | Residue/controller disposition | Sufficiency |
| --- | --- | --- | --- |
| A. Unknown read-only input FD, no output | Local reference reclaimed | Input unchanged; unsuccessful attempt; no artifact authority | Sufficient for local lifetime only |
| B. Partial private output exists | Local reference reclaimed | Persistent non-authoritative output; conservative accounting and controller cleanup/recovery | Death alone does not release/delete |
| C. Complete-looking unaccepted output | Local reference reclaimed | Reject success; completeness/digest is insufficient | Controller verification/failure rules remain |
| D. Local lease reference exists | That reference closes | Other holders may preserve liveness; authenticate orphanhood independently | Death alone does not authorize deletion |
| E. Another process has a duplicate | External reference survives | Existing topology/capability proof must exclude or account for it | Otherwise integration fails closed |
| F. Forbidden descendant survives | Parent local references close only | Topology violation; no child-cleanup inference | Integration fails closed |
| G. Residue fails recovery grammar | Exit does not repair residue | Existing fail-closed recovery; no new repair/deletion authority | Recovery remains blocked |

## 8. Status and authority separation

Status 12 remains exclusively the governed controller binding
`BOUNDED_CONTROLLER_ACQUISITION_OWNERSHIP_UNPROVABLE`. This worker rule MUST NOT use
12. A worker numerically returning 12 has not produced controller-retirement evidence.
The controller's acquisition-lifetime/RETIRING/non-returning-exit semantics are unchanged.

Status 70 remains `BOUNDED_PROJECT_IMPORT_SESSION_INTEGRITY`. Pinned-input acquisition
uncertainty MUST NOT be mapped to 70. If a separate genuine integrity condition
arises, its existing authority still governs that condition; it is not an alias.

No worker numeric status, range, wire enum, message, persistent resource ledger,
reservation category or cause-specific decoder is created. Existing generic
unsuccessful transport establishes failure only, not this internal cause.

## 9. Adversarial obligations

Each terminal-uncertainty row below requires §5 actual unsuccessful termination,
not merely an exception. Each residue row retains §7 accounting/recovery rules.

| # | Case | Required disposition |
| --- | --- | --- |
| 1 | INPUT_PROJECTOR normal pinned acquisition | Known owner verifies, transfers/disposes normally |
| 2 | INPUT_PROJECTOR ordinary open failure | Definitive failure; existing ordinary rejection, no unknown-FD inference |
| 3 | SIGINT before acquisition | Existing cancellation handling; no acquisition uncertainty from an unattempted call |
| 4 | SIGINT after kernel success before ownership proof | Unprovable classification selects irreversible failure and actual unsuccessful exit |
| 5 | Synchronous exception after known ownership | Existing known-owner cleanup/failure |
| 6 | Known FD uncertain close | Preserve non-retry disposition; do not relabel acquisition uncertainty |
| 7 | Unprovable ownership before output | Terminal failure; input unchanged; no output authority |
| 8 | Unprovable ownership with partial output | Terminal failure; partial residue stays charged/non-authoritative |
| 9 | Complete-looking output before unsuccessful exit | Reject success regardless of file/digest appearance |
| 10 | Hard worker termination | Actual death reclaims local FDs; persistent/external state remains |
| 11 | REPLAY_PREPARATION normal initial acquisition | Normal known ownership |
| 12 | Replay unprovable initial acquisition | Same terminal uncertainty rule |
| 13 | Replay normal delayed iterator reopen | Same known-owner rule on every reopen |
| 14 | Replay unprovable delayed reopen | Same terminal rule; initial validation gives no exception |
| 15 | Partial reconstruction output then failure | No trusted reconstruction; existing charge/recovery rules |
| 16 | Attempted useful continuation after uncertainty | Forbidden; catch/return cannot clear failed invocation; reach terminal exit |
| 17 | Buffered success-looking stdout before unsuccessful exit | Controller rejects it; no success authority |
| 18 | Worker numerically exits 12 | Not authorized by this rule; no controller-cause attribution |
| 19 | Worker status 70 | Only independently applicable integrity authority; never acquisition alias |
| 20 | Ordinary nonzero termination | Existing unsuccessful classification; no acquisition-cause proof |
| 21 | External duplicate | Local exit insufficient for external reclamation; require existing proof or fail closed |
| 22 | Forbidden descendant survives | Fail topology; parent death is not child cleanup |
| 23 | Another process retains lease | Liveness may persist; no orphan/deletion inference |
| 24 | Residue cannot authenticate | Existing recovery fails closed; no repair/deletion permission |
| 25 | Tracing-injected pre-ownership BaseException | If ownership unprovable, terminal failure; no new production instrumentation support |
| 26 | Signal-handler SystemExit in vulnerable interval | Classify; unprovable outcome cannot escape via catchable SystemExit into useful work |
| 27 | Repeated raising cancellation | No swallowed uncertainty or restored success; terminal selection dominates subsequent cancellation |
| 28 | Known-owner handoff interruption | Exactly one cleanup authority; preserve known-owner rules where ownership is provable |
| 29 | Controller has same technical uncertainty | Outside new worker authority; existing controller RETIRING/status 12 applies |
| 30 | Future worker writable/create acquisition | Outside scope; stop for separate authority, no read-only inference |

Self-review: actual termination is a readiness obligation, not a claim that current
catchable outer handlers already satisfy it. No diagnostic, shutdown hook or mutable
flag alone closes the terminal path. Nested catches and delayed acquisitions are
covered. No status-specific new cause is inferred. Read-only reclamation is not
filesystem rollback, charge release, child cleanup or publication authority.

## 10. Later implementation shape and adoption gates

Planning only: actor-neutral ownership migration is expected in
`src/orev3/execution/filesystem_capability.py` and consumers
`runtime.py`, `projection.py`, `external_inputs.py`, `dataset_validation.py`,
`replay_preparation.py` and `current_readiness.py` in the same package.
Controller policy belongs at controller runtime/evaluator and detached evidence
controller entry boundaries. Worker policy belongs at `input_projection_worker.py`
and `replay_preparation_worker.py` invocation boundaries, composed with
`bounded_streaming_worker_bootstrap.py` where that launcher generation applies.
Bootstrap integration must respect its frozen code-closure authority; this document
does not authorize changing any of these files or closure manifests.

Later isolated subprocess tests must prove real supported interruption handling,
every acquisition/handoff classification, delayed replay reopen, irreversible
failure despite catching/repeated cancellation, actual unsuccessful exit and
controller rejection of buffered results. Ownership tests must prove known-owner
cleanup/non-retry independently. Signal termination is observed by its actual wait
kind, not fabricated as a numeric cause. No live workload may be used for these tests.

The reviewed decision is adopted in-document only; Git effectiveness remains pending.
The adopted bytes require a new exact identity and independent verification that the
adoption diff changes only status, authority and adoption records. Git effectiveness
requires a separately authorized one-path commit, normal push to origin/research/post-v1
and independent verification of the parent, committed path, adopted bytes and live
remote. Implementation is separately
authorized afterward. Required sequence remains: clarification -> independent
review -> adoption -> Git effectiveness -> authorized cross-layer acquisition/pinned
ownership correction -> independent re-freeze -> only then separately authorized
Slice 4. This status edit activates nothing.

If terminal readiness requires a new status/meaning, another actor, worker write/create
or lock acquisition, spawn/PID ownership, unaccounted external copies or broader
recovery authority, stop rather than expanding this decision. A new worker number
has not been demonstrated necessary for the bounded local-FD safety property.

## 11. Non-authorizations

No implementation, worker status allocation, status-12/status-70 expansion, helper
migration, Slice-2 correction, Slice-4 implementation, native code, writer/IPC
activation, publication/dedup, RSS/watchdog activation, numeric-envelope adoption,
governed-host acceptance, readiness/Experiment-005, provider/outcome authority,
production adapter/registry/Source S, wallet/funding, transaction construction/signing/
submission, capital allocation, real-SOL activity or production mining is authorized.
Numeric mode remains `BOUNDED_STREAMING_MEASUREMENT_CANDIDATE`.
No comprehensive checkpoint is created or warranted by this clarification alone.
Stage 3C remains incomplete. This document is ADOPTED CLARIFICATION;
Git effectiveness is PENDING and NO IMPLEMENTATION AUTHORITY follows.
