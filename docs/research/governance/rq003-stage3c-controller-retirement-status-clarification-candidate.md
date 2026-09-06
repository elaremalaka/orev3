# Stage 3C controller acquisition-retirement exit-status clarification

**ADOPTED CLARIFICATION — GIT EFFECTIVENESS PENDING — NO IMPLEMENTATION AUTHORITY**

## 1. Authority and scope

Following exact-byte independent review and explicit user authorization, this
status edit adopts the reviewed clarification. Creation alone gave it no authority.
MUST/MUST NOT below become Git-effective only after separately authorized one-path
commit, normal push and independent live-remote verification. This edit performs
none of those steps and grants no implementation authority.

Reviewed candidate: 17552 bytes, 225 lines, SHA-256
`311643ed3939b131f04085c4a116a01e7e7ac69883c7bed6bfa891eac5ec2ba6`.
Independent review disposition:
`STAGE 3C CONTROLLER RETIREMENT-STATUS CANDIDATE REVIEW PASSED — EXPLICIT ADOPTION MAY BE CONSIDERED`.
The remote-backed HEAD recorded below remains unchanged by this status edit.

Upon Git effectiveness, this supplements ONLY the
unassigned controller retirement exit-status dependency in acquisition-lifetime §7.
It does not modify the trigger, cancellation, ownership, retirement or exit protocol.
All unrelated controlling requirements remain authoritative for their own scopes.

Authenticated repository: `/Users/erale/Documents/orev3`, branch `research/post-v1`,
tracking `origin/research/post-v1`; local/tracking/live-remote baseline
`fcc2f3f42c94c691b65012fab9d0c75bebc4ef94`, parent
`a7f0ea131237fd6f073f14a3d2fc8544920e6aba`, ahead/behind 0/0.

| Authority | Exact repository path | SHA-256 |
| --- | --- | --- |
| Controlling bounded-streaming prerequisite | `docs/research/governance/rq003-experiment-005-bounded-streaming-source-processing-prerequisite-v1.md` | `ce09153fc98145f3fa318a9c7e8dd563afbf4b64496e64535b27c49c93af90e3` |
| Recovery clarification | `docs/research/governance/rq003-stage3c-recovery-permission-clarification-candidate.md` | `7df413610a54adcacb06f5c01dc43b7ce2c04c5244922519871d745c0395f716` |
| Category clarification | `docs/research/governance/rq003-stage3c-category-attribution-clarification-candidate.md` | `2e735f2ffe1b4d537495dd7db62d75e21bb6db822c20863f5dc29781c508c101` |
| Admission-serialization clarification | `docs/research/governance/rq003-stage3c-admission-serialization-clarification-candidate.md` | `56b4e402a9b4e62853e285be3ed7ca7b7c2d1a0d34d71a7c9ee757b8dffdcfed` |
| Git-effective acquisition-lifetime clarification | `docs/research/governance/rq003-stage3c-acquisition-lifetime-clarification-candidate.md` | `1e2c235f11689cd64c65840b3055f377ebef8d9614ea31574e398a15bf29fdcd` |

The acquisition-lifetime clarification is 30330 bytes / 392 lines, committed at
`fcc2f3f42c94c691b65012fab9d0c75bebc4ef94`. Its historical Git-effectiveness-pending
status wording is not changed here; the authenticated commit/push/remote transition
established effectiveness. Its requirement for terminal-path readiness remains.

## 2. Existing status inventory and authority distinction

Read-only investigation covered repository governance/specifications, Stage-3
execution modules, boundary tests and related detached worker entry points. Numeric
search results are not a global allocation registry: ordinary programs may return
any representable value. The inventory below distinguishes project contracts from
implementation examples and external conventions; it does not redefine them.

| Status | Meaning and actor | Authority / implementation evidence | Exclusivity and conflict assessment |
| --- | --- | --- | --- |
| 0 | Successful worker/process exit | Controlling prerequisite lines 1264–1268; worker main returns; runtime `classify_bounded_worker_transport` | Cannot represent retirement; zero alone is not semantic evidence success |
| 1 | Ordinary Python/tool failure convention | Ordinary uncaught failures and Git/tool nonzero checks; not a dedicated controller retirement contract | Too general; not assigned to this condition |
| 2 | Ordinary worker invocation rejection | `preparation_worker.py:30`, `bounded_streaming_worker_bootstrap.py:905`; controlling prerequisite reserves worker validation/resource statuses 2–11 | Worker contract; no controller reuse |
| 3 | Worker request-path or command/environment rejection, actor-dependent | `preparation_worker.py:33`, `input_projection_worker.py:24`, `readiness_test_worker.py:55` | Not one universal symbolic error; worker contract |
| 4 | Worker request parsing, command or selector rejection, actor-dependent | `preparation_worker.py:37`, `evidence_preparation_worker.py:54`, `readiness_test_worker.py:65` | Worker contract |
| 5 | Worker command or source-working-directory rejection, actor-dependent | `preparation_worker.py:40`, `evidence_preparation_worker.py:57` | Worker contract |
| 6 | Detached preparation source-working-directory mismatch | `preparation_worker.py:44` | Within governed worker 2–11 block |
| 7 | Detached preparation Python environment rejection | `preparation_worker.py:46` | Within governed worker 2–11 block |
| 8 | Detached preparation fixed environment mismatch | `preparation_worker.py:57` | Within governed worker 2–11 block |
| 9 | Detached preparation network-denial validation failure | `preparation_worker.py:59` | Within governed worker 2–11 block |
| 10 | Worker rejection/exception or site-packages rejection, actor-dependent | `preparation_worker.py:62`; bootstrap outer exception exit at line 942; related projection/replay/readiness workers | Broad worker failure transport, not controller acquisition uncertainty |
| 11 | Detached preparation validation exception | `preparation_worker.py:70` | Within governed worker 2–11 block |
| 70 | `BOUNDED_PROJECT_IMPORT_SESSION_INTEGRITY`, bounded worker terminal integrity failure | Controlling prerequisite lines 1264–1299; bootstrap `TERMINAL_INTEGRITY_EXIT_STATUS = 70` and `_terminal` at line 543; runtime worker transport classifier; boundary tests assert returncode 70 | Explicit dedicated project meaning; MUST NOT be reused or broadened |
| 64–78 | Local sysexits named conventions: usage/data/input/user/host/service/software/OS/file/create/I/O/temporary/protocol/permission/configuration failures | macOS SDK `usr/include/sysexits.h`; notably 70 `EX_SOFTWARE`, 71 `EX_OSERR`, 74 `EX_IOERR`, 75 `EX_TEMPFAIL` | Platform conventions, not automatic project authority; 70 already has narrower worker contract |
| Signal termination | Signal identity, not an ordinary exit status | Runtime `decode_governed_wait_status` uses `WIFSIGNALED`/`WTERMSIG`; Python subprocess reports negative signal number | MUST remain distinct from exited status; shell encodings are not authority |
| External test/tool results | Tool-specific meanings; readiness worker also records pytest result as payload `exit_code` | `readiness_test_worker.py:70`; runtime/Git helpers reject nonzero subprocess results | Payload/tool status is not a controller terminal-status assignment |

In particular, controlling lines 1264–1268 explicitly bind `os._exit(70)` to the
worker integrity condition and distinguish it from success and ordinary statuses
2–11. Existing controller code rejects nonzero child results but does not establish
a general controller-fatal integer whose adopted semantics include acquisition
uncertainty. No such reusable controller assignment was found. Acquisition-lifetime
§7 itself explicitly leaves this exact status unassigned.

## 3. Criteria, platform evidence and options

Selection criteria, applied before assignment: a nonzero deterministic value,
separate from the identified project worker contracts and generic failure 1; no
misleading sysexits meaning; direct process-exit representation without truncation;
actor-aware testability; no shell translation; and no new range reservation.

Local platform evidence was read from:
`/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/usr/include/sysexits.h` and
`/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/usr/include/sys/wait.h`.
The sysexits table names 64–78; `EX__MAX` is 78. Its `EX_OSERR` examples concern
failed OS operations such as inability to create a pipe, whereas acquisition
uncertainty may follow a SUCCESSFUL syscall. `EX_TEMPFAIL` invites retry, which is
not this controller's permitted disposition. `EX_SOFTWARE` is broad and its integer
70 is already dedicated to a worker contract. These conventional meanings do not
uniquely fit the narrower condition and are rejected for this assignment.

Darwin wait decoding distinguishes normal exit from signal termination. The ordinary
exit status is represented through the low eight bits on the supported wait path;
12 is within 0–255 and needs no truncation or shell conversion. An isolated direct
CPython 3.14.5 subprocess running `os._exit(12)` was observed by `subprocess.run`
with `shell=False` as `returncode == 12`. This proves transport representability
only, not the future controller's retirement behavior or governed-host acceptance.
See [Python subprocess return codes](https://docs.python.org/3.14/library/subprocess.html#subprocess.CompletedProcess.returncode)
and [non-returning exit API](https://docs.python.org/3.14/library/os.html#os._exit).
No production process was terminated or signaled.

| Option | Fit, collision risk and implementation consequence | Decision |
| --- | --- | --- |
| Reuse controller-general fatal status | No applicable adopted assignment found; 1 is undifferentiated failure | Reject |
| Reuse 70 / EX_SOFTWARE | Broad conventional software failure, explicit conflicting project worker meaning | Reject |
| Use 71 / EX_OSERR, 74 / EX_IOERR or 75 / EX_TEMPFAIL | Confuses unknown acquisition ownership with syscall/I/O failure or retryable failure | Reject |
| Dedicated project-specific 12 | Lowest positive value after excluded generic 1 and governed worker 2–11 block; outside sysexits table; direct transport verified | SELECT |

The ordering criterion makes the choice reproducible, not aesthetic. Absence of a
search hit alone is not proof of global freedom: selection also rests on the explicit
closed worker contract, platform inventory, absence of adopted controller reuse,
and the narrow actor/trigger allocation made BELOW. This is a new project decision,
not a POSIX reservation or a claim that unrelated software cannot return 12. Future
assignments in this governed scope must preserve this dedicated meaning; no other
number or entire range is reserved by this clarification.

## 4. Exact adopted assignment and trigger

**Numeric exit status: `12`.**

**Canonical semantic identifier: `BOUNDED_CONTROLLER_ACQUISITION_OWNERSHIP_UNPROVABLE`.**

Meaning: controller acquisition/handoff ownership is genuinely unprovable under the
Git-effective acquisition-lifetime clarification; process retirement is required.
This is a terminal process-disposition identifier, not a new reservation wire failure
code, payload field, exception schema, worker result or numeric-envelope parameter.

Upon Git effectiveness, the governed controller MUST use status 12 for this
terminal path ONLY after the acquisition-lifetime rules classify ownership as
unprovable, process-wide RETIRING becomes authoritative, continued service is
irrevocably forbidden, and the non-returning terminal exit is required. The trigger
is inherited unchanged; the status cannot itself cause or authorize retirement.

An ordinary open error, definitive acquisition failure, known-owner cleanup failure,
known-FD uncertain close, ordinary exception, reservation denial, numeric-budget
rejection, worker failure, contended live lease or fail-closed orphan recovery MUST
NOT be relabeled with this identity merely because it is an error. If a separate
acquisition in handling such a condition becomes genuinely unprovable, only that
independently established acquisition-retirement trigger selects this status.

The value and identifier are controller-specific. Worker status 70 and ordinary
worker statuses 2–11 remain unchanged. A worker returning 12 does not become a
controller-retirement event; its result remains subject to existing worker rejection
rules. No existing worker decoder may infer this controller identity from a child
integer alone. No worker status is reassigned by this clarification.

## 5. Terminal path and preserved effects

The existing ordering remains: acquisition uncertainty -> irrevocable RETIRING ->
optional bounded independently safe housekeeping, if eligible -> non-returning
terminal process exit with status 12. The current CPython/POSIX route is
`os._exit(12)` or the acquisition clarification's supported equivalent with the same
exit property and status. `raise SystemExit(12)` alone is NOT equivalent.

The selected status must be available before acquisition retirement is enabled.
Adoption would resolve only the exit-status selection dependency; demonstrated
terminal-path readiness and separate implementation authorization remain necessary.
No logging, new acquisition, flushing, finalizer or atexit prerequisite is added.
Repeated cooperative cancellation cannot redirect RETIRING or change the assigned
status. Separately authorized hard termination may preempt normal exit: its observed
signal termination MUST NOT be misreported as status 12. No watchdog is activated.

Process exit reclaims local descriptor references, not filesystem effects, external
copies or children. A created file may remain; ordinary missing-lease roots still
fail closed; valid roots follow existing recovery; published objects remain outside
private deletion. Spawn/PID uncertainty is not brought into scope by assigning this
status. Parent status 12 neither proves nor authorizes child termination or deletion
of a root with a live worker lease. Accounting finality and reservation floors are
unchanged; observing this status cannot release disk charge by assumed cleanup.

## 6. Observability, collision and spoofing boundary

A bare integer 12 proves only that an observed process reported that exit value.
It is not cryptographic proof of the internal cause: an arbitrary program, worker,
wrapper or test can return the same number. Numeric uniqueness across all processes
is neither possible nor claimed.

Attribution to the canonical identity requires authenticated controller execution
identity/path plus evidence that this path selected RETIRING for the governed
acquisition-ownership condition and could not resume service. Future isolated
subprocess implementation tests must establish the trigger and expected terminal
state through controlled execution/injection and authenticate exited-kind status 12.
They must distinguish worker/other-process status 12, ordinary rejection, signal
termination, and a program simply returning 12. No persistent journal or required
terminal log is introduced; terminal exit must not depend on emitting evidence.

With that execution evidence, the status supports ONLY the acquisition-retirement
terminal disposition. It does not identify the unknown FD, prove all local disposal
steps ran, prove filesystem cleanup/root removal, prove child/worker termination,
or establish readiness, host acceptance, experiment validity or scientific authority.
Shell-derived values, PID guesses and exit-code coincidences cannot replace this
provenance. This changes no existing result-authentication contract.

## 7. Adversarial review and future obligations

| Case | Clarification disposition |
| --- | --- |
| Worker integrity failure | Existing worker 70; never controller 12 |
| Ordinary worker validation/resource failure | Existing actor-specific 2–11 contract |
| Ordinary acquisition failure or known-owner quarantine | Existing handling, not automatic 12 |
| Genuinely unprovable acquisition followed by RETIRING | Controller terminal status 12 |
| Multiple unknown local acquisition results | Same inherited retirement trigger, same status; no per-FD codes |
| Optional housekeeping fails | Existing unconditional exit path still uses 12 |
| Another program or worker returns 12 | No inferred controller cause; authenticate actor and path |
| Hard termination preempts exit | Record actual signal disposition; do not synthesize 12 |
| Shell reports a translated status | Insufficient; use authenticated direct process/wait interpretation |
| Retained file, live child or published object remains | Status proves no cleanup; existing authority controls each |
| Adoption without runtime readiness | Status assigned only after effectiveness; no activation or implementation authority |

Self-review found no collision with the identified governed statuses, no misleading
sysexits reuse, no representation loss for 12, and no known-owner/worker conflation.
This does not certify external supervisors or wrappers: any future wrapper must
independently preserve actor identity and status transport before its observations
can be used. A broad registry is unnecessary for this one scoped allocation.

## 8. Adoption, hardening and non-authorizations

The reviewed decision is adopted in-document only; Git effectiveness remains pending.
The adopted bytes require a new exact identity and independent verification that the
adoption diff changes only status, authority and adoption records. A separately
authorized one-path commit, normal push to origin/research/post-v1 and independent
live-remote verification must authenticate the parent, committed path and adopted
bytes before Git effectiveness. Implementation requires separate explicit
authorization afterward; terminal-path readiness remains a prerequisite.
Existing governance documents MUST NOT be silently reinterpreted by this status edit.

This reserves no range, prohibits no future separately governed controller status,
and prevents no later native acquisition hardening. Production/real-capital authority
may impose stronger requirements. This is a measurement/pre-production clarification
only; it does not establish production suitability.

No implementation, retirement activation, helper migration, Slice-2 correction,
Slice-4 implementation, native code, writer/IPC activation, publication/dedup,
RSS/watchdog, numeric-envelope adoption, governed-host acceptance, readiness,
Experiment-005, provider/outcome, production adapter/registry/Source S, Paper Miner
production, wallet/funding, transaction construction/signing/submission, capital or
real SOL authority follows. Numeric mode remains
`BOUNDED_STREAMING_MEASUREMENT_CANDIDATE`. The document is ADOPTED CLARIFICATION;
Git effectiveness is PENDING and NO IMPLEMENTATION AUTHORITY follows.
