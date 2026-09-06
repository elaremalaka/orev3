# Stage 3C recovery permission, ownership, and object grammar adopted clarification

## 1. Status and controlling authority

**ADOPTED CLARIFICATION — GIT EFFECTIVENESS PENDING — NO IMPLEMENTATION AUTHORITY.**

This adopted clarification supplements the recovery predicates of §9 of
[rq003-experiment-005-bounded-streaming-source-processing-prerequisite-v1.md](rq003-experiment-005-bounded-streaming-source-processing-prerequisite-v1.md),
whose exact controlling SHA-256 is
`ce09153fc98145f3fa318a9c7e8dd563afbf4b64496e64535b27c49c93af90e3`.
The exact controlling path is
`docs/research/governance/rq003-experiment-005-bounded-streaming-source-processing-prerequisite-v1.md`.
The controlling document is not amended by this artifact. Following exact-byte
independent review and explicit user authorization, this status edit adopts the
reviewed mode/UID/object-grammar and terminal-cleanup rules. All MUST, MUST NOT,
and SHALL statements become effective only after the separately authorized
commit, push, and independent live-remote verification described in §16.
The existing controlling document remains authoritative; unrelated requirements
are neither replaced nor superseded.

The terminal name `cleanup-<32 lowercase hex>` and its constrained promotion,
authentication, and durability protocol are **NEW ADOPTED SUPPLEMENTAL AUTHORITY,
PENDING GIT EFFECTIVENESS**. Existing controlling §9 does not already authorize
this terminal state. Its effectiveness follows §16; unrelated controlling
requirements are unchanged.
References to controlling sections below identify the frozen document; numbered
headings and explicitly local references identify this clarification.

The project objective remains an ORE miner eventually trustworthy with real
SOL. This clarification addresses one concrete recovery blocker toward that goal;
it grants no authority to operate with SOL. Numeric mode remains exactly
`BOUNDED_STREAMING_MEASUREMENT_CANDIDATE`.

## 2. Verified problem and evidence

The controlling §9 expressly assigns mode 0600 to `coordination.lock` and
`lease`, mode 0700 to the operation root, and rejects links, special files,
duplicate inodes, invalid modes, and escaping paths during orphan recovery.
Controlling §10.1 expressly requires an exclusive mode-0600 bootstrap request,
descriptor authentication including owner, and a read-only request descriptor.
Neither read-only descriptor access nor semantic immutability specifies a
read-only inode mode.

Re-reading controlling §§3, 7–9, 9.1, and the launch/request provisions of
controlling §10.1 confirms
that they do not complete the private-directory/payload mode predicate,
recovery-wide expected UID/GID authority, or the descendant grammar. “Invalid
mode” cannot deterministically decide these omitted cases. This is a genuine
governance gap, not permission to infer requirements from implementation.

Read-only implementation observations are supporting compatibility evidence,
not controlling authority: `runtime.py` creates the request at
`bounded-bootstrap-request.json` directly beneath its supplied operation root;
it uses more than one private creation convention elsewhere.
`filesystem_capability.py` requests private creation modes and separately
applies 0444 to authenticated published targets after temporary-name removal.
These observations neither authorize private 0444 nor prove present code
conforms to this clarification. No code was changed or executed for this analysis.

The original candidate allowed lease unlink while an ordinary root still
existed. A controller crash before root removal then left a lease-less ordinary
root without persistent orphan proof: safe refusal, but non-convergent cleanup.
The adopted correction defines one terminal namespace state entered only
after authenticated orphan cleanup has drained the ordinary root to its lease.
Its directory name persists across lease unlink, and final empty-directory
removal removes both residue and proof. This does not make unlink and directory
removal atomic or create automatic authority for ordinary missing-lease roots.

## 3. Scope and preserved authority

Only recovery acceptance of the existing private storage objects is clarified:
type, permission bits, owner, structural placement, crash-state treatment, and
validation ordering, with one new controller-owned terminal namespace state
needed for restartable terminal deletion. This is not general filesystem
security policy, a new payload/storage category, scientific policy, or a
redesign of publication or ordinary lease-based liveness.

The following remain unchanged:

- Controller-owned operation, coordination, ledger, recovery, and deletion
  authority; worker claims never establish recovery authority.
- Descriptor confinement, no symlink following, and the existing link,
  special-file, duplicate-inode, and escaping-path rejection conditions.
- Exact controller-generated `op-<32 lowercase hex>` identifiers, their
  existing CSPRNG rule, and the existing 128-collision boundary.
- Coordination locking and lease flock authority, including inherited worker
  lease lifetime under controlling §§9 and 9.1. PID, age, timestamps, and worker messages
  are not substitutes.
- Checked uint64 accounting, logical-size charging, existing resource rules,
  fsync/recheck requirements, no semantic resume, and no trusted partial output.
- Separate publication authority, source/outcome placement restrictions, and
  all controlling §10.1 launch, descriptor, request-content, and identity checks.

No inventory depth/cardinality limit, byte ceiling, timeout, retry count,
RSS limit, watchdog value, or final numeric envelope is introduced. In
particular, a legacy implementation value such as 100000 is not recovery
policy. Inability to complete validation is failure, not permission to skip
objects or invent a limit.

This correction introduces NO cleanup marker file, cleanup journal, persistent
resume journal, persistent logical ledger, cleanup payload, scientific artifact,
new reservation category, or worker-visible resume state. The terminal namespace
state is the only new persistent proof/state.

## 4. Options and decision rationale

| Question | Options evaluated | Adopted decision and reason |
| --- | --- | --- |
| Private modes | A: exact 0700 directories/0600 files; B: exact metadata plus payload modes such as {0600, 0400} | Select A. No governed private lifecycle requires 0400. Immutability and read-only FD access do not require chmod. B would add an unnecessary accepted state. |
| Subset predicates | Any permissions no broader than 0600/0700 | Reject. This would admit, for example, unusable 0000 objects without a governed lifecycle or a deterministic reason to accept every subset. |
| Creation mismatch | Fail closed; or normalize only freshly created objects and reauthenticate | Select fail closed. It needs no mutation exception or proof of normalization eligibility and respects the existing exact metadata predicates. A restrictive umask can reject creation; that is an explicit availability tradeoff. |
| Owner | Controller effective UID alone; UID plus effective GID; UID plus parent-derived GID | Select UID alone with exact private modes. Group/other permission bits are absent. No existing recovery authority makes either process GID or inherited directory GID the required owner group. |
| Descendants | Enumerate every payload filename; or accept arbitrary contents everywhere; or close structural names and constrain payload descendants | Select the third. It supports partial outputs and nested private work without turning arbitrary root entries into structural authority. |
| Terminal cleanup | Lease-last ordering; internal/external marker; or one terminal name for the drained root | Adopt the terminal name. Lease-last and an internal marker retain a final unlink gap; an external marker needs another persistent object and lifecycle. A same-parent terminal name keeps the proof until empty-root removal without any marker payload. |

This is the smallest safe clarification because it extends already-explicit
private modes, fixes one owner source, and closes only structural names.
It adds no lifecycle chmod, recovery repair, cross-user mechanism, scientific
filename interpretation, or numeric policy. Its sole additional lifecycle
authority is the explicit terminal name/protocol, not an inference from naming
conventions. Existing code conventions remain subject to future separately
authorized implementation review.

## 5. Recovery object taxonomy and exact modes

Mode means all permission and special bits, equivalent to `stat.S_IMODE`,
validated separately from the inode type. Every predicate below is **exact**,
not a subset and not a finite set with additional values. Thus setuid, setgid,
and sticky bits are excluded as well as group/other access.

| Object class | Required inode type | Exact accepted mode |
| --- | --- | --- |
| Private snapshot-store root used as the coordination anchor | Directory | 0700 |
| `.orev3-bounded-streaming-v1/` | Directory | 0700 |
| `operations/` | Directory | 0700 |
| `op-<32 lowercase hex>/` | Directory | 0700 |
| `cleanup-<32 lowercase hex>/` terminal root | Directory | 0700 |
| Four operation-private subdirectories and all permitted nested directories | Directory | 0700 |
| `coordination.lock` | Regular file | 0600 |
| `lease` in an ordinary root or terminal T1 state | Regular file | 0600 |
| Bootstrap request, including the permitted direct-root request entry | Regular file | 0600 |
| Ordinary private payload, controller temporary, and worker output files | Regular file | 0600 |
| Any already-authorized stdout/stderr capture file stored inside operation authority | Regular file | 0600 |
| Private projection/reconstruction candidates and snapshot/publication temporaries inside operation authority | Regular file | 0600 |
| Published content-addressed files outside operation authority | Separate publication authority | Not judged by this private-file predicate |

The snapshot-store root's directory metadata is checked as an anchor; this
MUST NOT extend private orphan inventory to its published contents. Ancestors
outside this private anchor retain existing capability/confinement rules;
this clarification does not demand 0700 or controller ownership of `/`, a home
ancestor, or unrelated repository directories.

## 6. Creation, umask, and authentication

The controller MUST request 0700 for governed directories and 0600 for
governed files, using the existing exclusive/no-replacement creation and
no-follow descriptor confinement rules. Requested mode, resulting mode, and
recovery-accepted mode are distinct facts: POSIX/macOS umask can remove bits,
so `open(..., 0600)` or `mkdir(..., 0700)` alone does not establish exactness.

Every newly created governed object MUST have its resulting type, mode,
UID, identity, and confinement authenticated through its pinned descriptor
before it becomes authoritative or usable for payload processing, lease or
coordination authority, or worker launch. Obtaining a descriptor solely for
this authentication is not payload use. Exclusive creation alone is not
authentication. The creator MUST reject if it cannot obtain/authenticate the
object safely, or if the resulting mode differs from the table.

The chosen rule is **fail closed, not normalization**. This clarification does
not authorize chmod, fchmod, chown, or changing process umask to repair either
new or pre-existing objects. It also does not introduce a recovery-time repair
exception. A failed creation MUST NOT be admitted; any retained state is
subject to the same recovery and liveness checks. It cannot be silently
accepted because the mode looks more restrictive.

A terminal directory MUST NOT be independently created by mkdir or a general
creation path. It may arise only by the authenticated promotion in §10.
Promotion retains the existing inode and permissions and requires descriptor
reauthentication; it is not a mode-normalization exception.

## 7. Recovery-time modes and lifecycle

Recovery MUST observe and authenticate existing modes without changing them.
There are no legitimate permission-mode transitions while an inode remains a
private operation object under this clarification. Zero-length, partially written,
completed, closed, and semantically immutable private files all require 0600;
all present private directories require 0700. Modes 0400 and 0444 are not
accepted private-file lifecycle states. Read-only file descriptors remain
compatible with an inode at 0600.

Publication may have its separately governed lifecycle. It MUST NOT cause a
still-private name to bypass private validation, or let private recovery
follow a published alias. This clarification neither changes the temporary-plus-
link mechanism nor waives its existing recovery rejection conditions. If a
crash leaves a linked/duplicate or otherwise unauthenticatable private entry,
recovery fails closed; it does not repair that state or delete the published
object. Broader reconciliation of such state requires separate authority.

## 8. Normative ownership predicate

Before admitting private storage authority or beginning reconciliation, the
controller MUST capture its effective UID from the operating system as the
expected controller UID. It MUST authenticate that identity remains the same
through recovery and admission; identity change or inability to authenticate
it fails closed. The source MUST NOT be a worker claim, request field,
pathname owner chosen after inspection, username, or a lease's self-report.

Every in-scope directory and regular file in §5 MUST have descriptor-derived
`st_uid` equal to that captured UID. A later recovery controller derives its
own expected UID the same way and compares existing objects against it. It
MUST NOT adopt another UID from recovered state, even when running with
privileges that would permit accessing it. This is not cross-user recovery.

**GID equality is intentionally not part of the acceptance predicate.**
Neither `getegid()` nor a parent's GID establishes an expected recovery GID.
Exact modes exclude group access and directory setgid. This does not remove
existing metadata-stability checks: where owner metadata is compared before
and after authentication, unexpected GID mutation still fails that stability
check. It simply does not impose equality to an invented expected GID.

## 9. Private object grammar

The coordination subtree SHALL have this closed structural grammar:

```text
<authenticated private snapshot-store root>/
  .orev3-bounded-streaming-v1/
    coordination.lock
    operations/
      op-<32 lowercase hex>/
        lease
        controller/
        worker/
        snapshot-publication/
        reconstruction/
        bounded-bootstrap-request.json   [optional regular file]
      cleanup-<32 lowercase hex>/
        lease                           [T1: sole entry; T2: absent, root empty]
```

The four directory spellings above are this clarification's explicit mapping of
controlling §9's controller, worker, snapshot-publication, and reconstruction
roles.
A fully initialized operation MUST contain all four and its authenticated,
held lease. The optional direct-root request spelling is selected explicitly
to accommodate the existing frozen request-creation convention, not because
code independently creates governance. It is the sole permitted additional
direct-root file; it is not required before a launch is prepared. All controlling §10.1
request requirements still apply when a request is used.

No other entry directly under the coordination subtree, `operations/`, or an
ordinary operation root is accepted. Direct children of `operations/` MUST be
ordinary `op-<32 lowercase hex>` directories or terminal
`cleanup-<32 lowercase hex>` directories. No other naming class, shared cleanup
directory, marker, file, or renamed-root fallback is accepted. Unexpected
structural entries fail recovery closed and are not silently skipped, deleted
as generic debris, or recategorized as payload.

Beneath each of the four private directories, ordinary regular files and
nested directories are permitted recursively, with exact type/mode/UID and
confinement checks on every present entry. Payload names need not be
pre-enumerated. Each name MUST be an actual single directory-entry component;
`.` and `..` are not descendants, and no path traversal, path separator,
symlink, special file, alias, or escaping lookup is accepted. Hard links and
duplicate inodes remain rejected under controlling §9; regular files MUST have one link.
Directory link counts MUST NOT be mistaken for the regular-file one-link
predicate. Encountered device/inode identities MUST not repeat in an orphan
inventory, including across the operation roots being reconciled.

This payload grammar is authority to inventory/discard confined orphan bytes,
not authority to produce arbitrary bytes or new artifacts. Existing source,
outcome, output, storage-category, and worker restrictions still govern
creation and use. An arbitrary file's content is never parsed as proof of
liveness, completion, identity, or scientific validity. No filesystem socket
entry is introduced: controlling §9 uses an anonymous socket pair. Stdout/stderr
remain pipes under controlling §10.1; the file row in §5 only classifies an already-authorized
capture, and authorizes no new capture or change to fixed descriptors.

### 9.1 Terminal grammar and binding

Here `<id>` denotes exactly the 32 lowercase hexadecimal suffix of the original
`op-<id>` identifier. The terminal name MUST be exactly `cleanup-<id>`, binding
one-to-one to that original operation. It MUST be a direct child of the same
authenticated `operations/` directory, of directory type, exact mode 0700,
and the governed effective UID, with stable descriptor-authenticated identity
and confinement. Existing link, duplicate-inode, and substitution rejection
rules apply.

Exactly two terminal content states are valid:

| State | Exact permitted content |
| --- | --- |
| T1 — lease present | Exactly one entry, `lease`: descriptor-authenticated regular file, exact 0600, governed UID, and existing link/inode predicates. |
| T2 — empty | No entries other than filesystem dot entries; emptiness must be authenticated through the confined directory authority. |

No payload, private subdirectory, bootstrap request, stdout/stderr capture,
reconstruction candidate, publication temporary, nested directory, symlink,
hard link, special file, or arbitrary metadata is permitted in terminal state.
Unexpected contents MUST fail closed, not be recursively repaired/deleted.
The ordinary recursive descendant grammar does not apply to terminal roots.

If both `op-<id>` and `cleanup-<id>` are visible, recovery MUST fail closed.
It MUST NOT merge, delete either, select one as authoritative, rename one, try
another identifier, or admit new work. This contradiction requires separate
reconciliation/governance/operator action. Detect it across the structural
namespace before destructive recovery, and recheck binding at each transition.

### 9.2 Controller-exclusive terminal authority

A matching terminal pathname is NOT self-authenticating and is never deletion
authority by itself. Authority depends on the adopted protocol invariant that
only the governing controller may create terminal state through §10's
authenticated, exclusive promotion. Every discovered terminal directory MUST
still pass the complete applicable descriptor/name/mode/UID/type/confinement/
identity/content predicate before use.

Workers MUST NOT create operation structural entries or cleanup names, rename
ordinary or terminal roots, unlink operation structural names, modify
coordination metadata, or perform terminal promotion. Mode 0700 alone does NOT
isolate a same-UID worker. The existing Stage-3 capability/launcher/Seatbelt
boundary MUST exclude worker mutation of these structural namespace entries.
This clarification does not prove governed-host acceptance of that boundary.
Unestablished controller-exclusive mutation authority blocks use of terminal
proof; worker statements cannot supply it.

This preserves the existing trusted-controller model. It does not claim that
mode/UID/name checks can detect a perfect namespace forgery by an actor with
trusted-controller-equivalent authority. No worker capability or authority is
expanded to accommodate terminal recovery.

A terminal root MUST NOT be independently created, receive a fresh random ID,
be selected by a caller or worker, or be synthesized from arbitrary residue or
a missing-lease ordinary root. Promotion is one-way: no
`cleanup-<id> -> op-<id>` transition exists. Terminal roots MUST NOT be reused
for worker execution, bootstrap, output generation, projection, reconstruction,
publication, reservation/accounting growth, scientific recovery, or new
operation admission. They carry no scientific, resume, publication, worker,
reservation-category, or payload authority.

## 10. Partial initialization and cleanup

For ordinary roots, absent payload files, empty files, truncated request/payload
bytes, empty nested directories, and any subset of the four named directories
are valid **structural partial states**, provided every present entry authenticates.
They are not complete admission states and do not by themselves establish
orphanhood. Recovery need not semantically authenticate an abandoned request
or projection merely to discard it after valid lease classification; controlling
§10.1 content authentication remains mandatory before use or launch.

| Ordinary-root state | Disposition |
| --- | --- |
| Authenticated root/lease; exclusive nonblocking lease flock reports lock contention | Live: leave the root untouched, including partial payload/initialization state. No recursive orphan inventory or deletion. |
| Authenticated root/lease; exclusive nonblocking lease flock succeeds; present descendants pass complete validation | Recoverable orphan, even with missing private subdirectories or partial files. Hold the acquired lease through confined cleanup. |
| Lease missing, wrong type/mode/UID, replaced, or otherwise unauthenticatable; non-contention flock error | Unclassifiable: fail closed, even if root is empty. Neither a missing lease nor apparent cleanup history proves orphanhood. |
| Present structural/payload entry violates grammar, mode, owner, link, or confinement rules | Invalid: no successful recovery/admission; no attempt to repair the entry into validity. |

The lease has no new JSON or PID-content grammar: its authenticated inode and
kernel flock state are the liveness authority. “Malformed lease” here means
failure of that existing authority, not an invented semantic lease record.

Initialization MUST remain under the coordination lock until its lease is
authenticated and held and its required structural directories authenticate;
no operation payload use or worker launch precedes complete initialization.
Cleanup MUST retain the authenticated lease while deleting all non-lease
contents, including the four directories. The controller MUST NOT unlink the
lease while the root remains in ordinary `op-<id>` state. It MUST use the
terminal-promotion protocol below before destroying the lease pathname.

An ordinary root left by a crash before a usable lease exists remains
UNCLASSIFIABLE / FAIL CLOSED, even if empty. Terminal state MUST NOT be used
to resolve pre-lease initialization crashes, a lost ordinary lease, or
arbitrary residue. Promotion requires prior ordinary-lease orphan proof.
Crashes during ordinary payload cleanup remain recoverable by a fresh
authenticated lease classification; terminal crashes follow §10.3.

A wholly absent coordination subtree is an initialization case, not orphan
proof. Present shared structural entries MUST authenticate before exclusive
creation of missing shared structure. A missing coordination lock with any
existing ordinary or terminal operation root MUST NOT be replaced to claim
coordination authority; reconciliation fails closed. Missing `operations/` may be initialized only
after valid coordination locking and closed-grammar verification. Recovery
MUST NOT delete the shared anchor or coordination metadata as orphan contents.

### 10.1 Ordered terminal-cleanup protocol

Every step below is adopted supplemental authority, effective only after §16's
commit, push, and independent live-remote verification.
The controller MUST hold required coordination authority throughout cleanup,
promotion, terminal removal, and final recheck; it MUST retain its acquired
lease exclusion through the terminal transition as applicable.

1. **Authenticate ordinary orphan.** Descriptor-authenticate `op-<id>` as a
   confined stable directory, exact 0700 and governed UID. Authenticate its
   exact `lease` as a confined stable regular file, exact 0600 and governed
   UID, satisfying existing link/inode requirements. Acquire the governed
   nonblocking exclusive lease flock. Contention means live: leave untouched;
   other lock failures reject. No destructive cleanup precedes this proof.
2. **Inventory before deletion.** Complete the confined ordinary orphan
   inventory and checked uint64 logical-size reconstruction. Invalid mode/UID,
   symlink, prohibited hard link, duplicate inode, special file, escaping
   path, invalid structure, arithmetic overflow, or any other already-governed
   unsafe state MUST reject before destructive cleanup of that root.
3. **Drain to lease-only.** Descriptor-relatively delete authorized non-lease
   descendants, retaining the authenticated lease. Remove all payloads, all
   four private subdirectories and descendants, and the optional bootstrap
   request. Preserve accounting reconciliation and identity/confinement
   checks through deletion.
4. **Reauthenticate immediately before promotion.** Require the ordinary
   root to contain EXACTLY its authenticated lease. Reauthenticate root and
   lease type, exact mode, UID, identity, link predicates, and confinement;
   require held lease exclusion, destination absence, and no conflicting
   same-ID namespace state. No weaker state may be promoted.
5. **Establish pre-promotion durability.** Complete the synchronization/
   durability operations required by the governed filesystem model to
   establish the drained lease-only state before relying on promotion.
   Failure blocks promotion; no success or weaker fallback is permitted.
6. **Promote exclusively under the same parent.** Rename only that same
   authenticated root from `operations/op-<id>` to
   `operations/cleanup-<id>`, descriptor-confined and without replacement.
   No overwrite, merge, cross-filesystem move, copy/delete emulation, reverse
   promotion, or weakening path-based fallback is permitted. A pre-existing
   destination fails closed: no alternate cleanup ID and no ordinary
   operation-ID collision retries are available for this transition.
7. **Authenticate the promoted state.** Require ordinary source absence,
   terminal destination presence, exact suffix binding to the original
   operation ID, directory type/0700/governed UID, stable confinement, and
   the same promoted root identity using the platform's qualified identity
   model. Require the same authenticated lease as the sole entry and no
   conflicting ordinary root. Inability to establish identity continuity
   fails closed; a pathname is not a substitute.
8. **Durably establish terminal namespace before lease destruction.**
   Synchronize the authenticated `operations/` parent as required by the
   governed storage model. Once the lease pathname is destroyed,
   `cleanup-<id>` becomes the persistent restart proof; that namespace
   transition MUST therefore reach its required durability point first.
   Synchronization failure MUST stop before lease unlink.
9. **Unlink terminal lease.** Only after step 8, unlink the lease through the
   authenticated terminal-root descriptor. Keep current controller
   coordination/lease authority as applicable; do not deliberately release
   exclusion early. An open lease descriptor alone is not restart proof.
10. **Synchronize and authenticate empty terminal root.** Perform required
    terminal-directory synchronization after lease removal; reauthenticate
    stable identity, mode/UID/confinement, and EMPTY contents. Any unexpected
    entry rejects rather than triggering recursive repair.
11. **Remove empty terminal root.** Remove `cleanup-<id>` only through the
    authenticated operations-directory authority after T2 authentication,
    including absence of conflicting `op-<id>`. This is the sole
    lease-less-root deletion exception.
12. **Establish parent durability.** Synchronize the authenticated operations
    parent as required after terminal-root removal. Failure prevents success.
13. **Final recheck.** Reauthenticate the operations namespace; require both
    names absent, no unresolved contradiction introduced by cleanup, and all
    required recovery invariants satisfied.
14. **Admission.** Only successful completion of the entire recovery pass and
    its final namespace recheck may report recovery success or permit later
    admission. Existing authenticated live ordinary roots remain untouched.

All promotion preconditions are cumulative. Descriptor identity/binding MUST
remain stable through the transition; destination presence or same-ID
coexistence MUST NOT be resolved by choosing a different name. Promotion is
not a new operation-ID generation event and changes no collision envelope.

Terminal promotion creates no new logical charge. Before promotion all
non-lease payload has been accounted/reconciled through ordinary cleanup.
The lease retains the zero logical length stated by the controlling
measurement-mode accounting; it supplies no new status-content protocol.
Directories/terminal names are structural proof, not a new reservation category
or scientific/logical charge for directory-entry metadata. Checked accounting,
existing charges until verified deletion, and numeric mode are unchanged.

### 10.2 Terminal restart and platform qualification

For **T1**, a later controller MUST acquire coordination authority, authenticate
the terminal directory/name/type/0700/UID/confinement/identity and the sole
lease's type/0600/UID/link/inode predicates, then obtain a fresh governed
nonblocking exclusive lease flock. It MUST distinguish contention from other
errors; either contention or an invalid/unclassifiable terminal lease blocks
success, leaves the root untouched, and never permits lease deletion.
Reauthenticate the root as lease-only after acquisition. The previous
controller's flock is not persistent evidence.

The later controller MUST re-establish the required operations-parent
durability barrier before unlinking a T1 lease, even if the rename is visible
or believed durable. It MUST perform any preceding synchronization required by
the qualified storage model. Synchronization failure stops before the
proof-destroying transition. Then continue steps 9–14.

For **T2**, a later controller MUST authenticate the terminal canonical name,
directory type, exact 0700, governed UID, stable descriptor identity,
confinement, emptiness, absence of conflicting ordinary root, and namespace
consistency. Under the controller-exclusive promotion invariant, this empty
terminal state is the persistent proof that ordinary orphan authentication
preceded lease destruction. Continue required terminal synchronization/removal,
parent durability, and final recheck. This exception MUST NOT apply to an
ordinary `op-<id>` without an authenticatable lease.

Later implementation/acceptance MUST establish the required host/filesystem
semantics: same-parent rename with no destination replacement, descriptor
confinement, required directory synchronization/durability operations, stable
identity comparisons, descriptor-relative deletion, and nonblocking exclusive
flock behavior. Unsupported or unauthenticatable semantics fail closed; no
replacing rename, path-based recursive deletion, copy/delete emulation,
cross-filesystem move, PID/mtime/age inference, unreviewed stronger
synchronization API, or weaker filesystem fallback is authorized.

This clarification requires synchronization barriers at proof transitions; it
does NOT claim that fsync makes lease unlink plus directory removal atomic.
Controller/process-crash restart semantics are distinct from stronger
power-loss/storage durability claims. Successful fsync does NOT prove every
possible power-loss ordering guarantee on every storage stack. Stronger
guarantees remain subject to later governed-host storage qualification and
acceptance evidence. This clarification does not introduce F_FULLFSYNC or another
stronger primitive. Governed-host acceptance remains DEFERRED, and is blocked
on a host/filesystem unable to establish the required protocol semantics.
The clarification itself proves no host acceptance.

### 10.3 Second-order crash dispositions

These dispositions require the recovered state's full predicate; no row
authorizes interpreting an unauthenticated name as proof.

| Crash/state | Required restart disposition |
| --- | --- |
| A — Before promotion | Ordinary `op-<id>/lease`: authenticate ordinary root/lease, reacquire exclusion, reclassify orphanhood, and repeat remaining ordinary cleanup. |
| B — During/around promotion | Exactly one valid ordinary lease-present state OR terminal T1 may proceed after full authentication and lease exclusion. Contradictory, ambiguous, duplicated, substituted, or unauthenticatable state fails closed. |
| C — Rename visible, prior durability unknown | Authenticate T1, reacquire lease, reauthenticate lease-only contents, and re-establish parent durability before lease unlink. |
| D — Durable terminal state with lease | Fresh T1 authentication/exclusion is still required; repeat required restart barriers and continue. |
| E — Crash after terminal lease unlink | Authenticate empty T2, including stable mode/UID/confinement and no conflicting ordinary root; remove only that empty terminal directory through confined authority. Ordinary missing-lease roots do not qualify. |
| F — Terminal root removed, parent durability incomplete | Reauthenticate recovered operations namespace. If both names are absent, continue required reconciliation/durability/recheck. If valid terminal residue is exposed, apply T1/T2 rules. Invalid or contradictory state fails closed. |
| G — Terminal removal durable | No residual root and no separate proof object remain: empty-root removal removed both residue and namespace proof. Complete final recovery recheck before admission. |
| H — Malformed terminal state | Wrong mode/UID/name/type, unexpected content, links, special files, duplicate inode, conflicting ordinary root, unclassifiable lease, or namespace substitution fails closed without recursive repair. |

A crash before an ordinary lease exists remains the distinct unclassifiable
initialization case. Under qualified process-crash semantics, the new normal
terminal states retain either fresh lease proof or authenticated empty-terminal
proof until removal; no separate final marker unlink recreates the defect.
This does not promise automatic repair of corruption or storage behavior
outside the qualified model.

## 11. Validation ordering

1. Capture controller identity; pin and authenticate the private anchor and
   coordination directory/lock without following links. Acquire exclusive
   coordination flock; reauthenticate identity/binding before use. Under this
   authority, revalidate the applicable anchor/coordination namespace and keep
   coordination authority through reconciliation, terminal cleanup and admission.
2. Authenticate `operations/` and enumerate structural entries without following
   links. Classify exact ordinary `op-<32 lowercase hex>`, exact terminal
   `cleanup-<32 lowercase hex>`, or invalid names. Invalid structural entries
   reject. Detect same-ID ordinary/terminal coexistence before destructive
   recovery; coexistence rejects without deleting or choosing either entry.
3. For each ordinary root, authenticate descriptor/type/0700/UID/confinement
   and required lease/type/0600/UID/link/identity. Missing or unauthenticatable
   lease rejects. Only actual nonblocking exclusive flock contention means
   live: leave that root untouched. Successful acquisition establishes orphan
   authority; other lock errors reject.
4. Do not recursively inspect live ordinary descendants as an orphan inventory.
   Live classification does not claim every changing payload has been audited;
   any unsafe state actually observed still prevents recovery success.
5. For each positively classified ordinary orphan, retain the lease and validate
   its complete structural/payload inventory before its first deletion.
   Reconstruct all unique regular-file logical sizes, including lease/request
   files, using checked uint64 arithmetic. No worker ledger or published
   object substitutes for descriptor-derived state. Drain and promote only
   through §10.1; ordinary lease unlink is prohibited.
6. For each terminal root, authenticate its exact name, descriptor/type/0700/
   UID/confinement/identity, and inspect only enough contents to establish T1
   lease-only or T2 empty. Anything else rejects; never apply ordinary
   recursive payload deletion to terminal contents.
7. For T1, authenticate the lease and obtain fresh exclusive nonblocking flock.
   Contention or other invalid state fails closed without deletion. Reauthenticate
   lease-only state and re-establish required parent durability before unlink;
   complete terminal cleanup under §§10.1–10.2.
8. For T2, authenticate emptiness and namespace consistency; complete required
   terminal synchronization, remove only the empty terminal root, synchronize
   parent, and recheck. A missing ordinary lease does not use this branch.
9. After all recoverable ordinary orphan and terminal states are reconciled,
   re-enumerate/recheck the structural namespace. Require no unsafe,
   contradictory, unclassifiable, or unresolved state; preserve live ordinary
   roots untouched. Only then report recovery success or permit later admission.

All deletions/promotions MUST preserve stable descriptor-to-entry binding and
confinement against substitution. A pre-scan followed by a string-based remover
is insufficient. A failure after partial deletion does not permit success;
apply the exact recovered state on the next pass. Validated cleanup of an
earlier root does not license deletion of a later invalid root.

## 12. Published-object separation

Published content-addressed snapshots and projections retain controlling
§§3 and 9 and
existing publication authentication. Legitimate published 0444 objects are
not invalidated by the private 0600 rule. Conversely, their mode, digest-like
names, or hard-link relationship cannot authorize private 0444 or exempt a
private entry from inventory validation.

Only actual descendants of the governed confined operation root may be
removed by orphan recovery. It MUST NOT traverse, inventory as orphan charge,
chmod, or delete published store contents. Authenticating the snapshot-store
anchor does not merge publication and operation authorities. Publication
crash remnants that violate existing private link rules stay unresolved and
block successful recovery; this clarification does not silently expand cleanup
into publication reconciliation.

Terminal promotion MUST NOT rename or move a published object or confer
publication authority. Private publication temporaries MUST be removed under
ordinary authenticated orphan cleanup before lease-only promotion. Linked
publication residue rejects rather than being followed/deleted, and any
unexpected terminal publication content fails closed.

## 13. Fail-closed disposition and compatibility

Unknown grammar, mode/UID mismatch, failed metadata authentication, links,
special files, duplicate inodes, escaping or unstable bindings, unclassifiable
leases where required (ordinary roots and terminal T1), arithmetic failure,
or incomplete deletion/recheck MUST prevent successful recovery and new admission. Recovery MUST NOT silently skip the
state, normalize it, trust a worker explanation, or treat it as orphaned.
Existing closed failure reporting remains; no new failure-code schema is
created here.

The exact modes extend controlling §9's existing private root/metadata pattern.
Controlling §10.1's read-only FD 6 remains compatible with 0600 and retains its stronger
content and stability checks. Controller ownership extends its owner check
with a deterministic source rather than a GID convention. Recursive payload
acceptance preserves partial outputs, while closed root entries prevent an
unbounded structural interpretation. Private immutable candidates remain
semantically immutable through existing authority; chmod is not that proof.

The deliberate fail-closed limits remain restrictive umask, ordinary
missing-lease/partial-initialization states, and already-rejected linked
publication remnants. The terminal correction does not resolve those cases.
It adopts one new state to close the normal terminal cleanup crash window:
ordinary lease proof is retained until terminal namespace proof reaches the
required durability point, and empty terminal-root removal removes proof and
residue together. This is an explicit addition to controlling §9, not a claim that the
previous ordinary-name grammar already supplied terminal authority.
No ordinary liveness, publication, numeric, or worker authority is weakened.
Broader recovery mechanisms require separate governance.

## 14. Implementation consequences for Slice 2

After §16's effectiveness verification **and separate implementation authorization**, Slice 2 can use
one exact private mode/UID predicate, the structural grammar above, recursive
confined payload validation, and lease-first orphan classification. It must
distinguish complete admission structure from recoverable partial structure,
creation requests from authenticated modes, and private inventory from
published-object authority. It must preserve the frozen Slice-1 boundary.

This document changes no implementation path and supplies no patch, operational
reservation integration, test changes, configuration, or schema. If future
work finds that satisfying it requires changes to frozen Slice 1 or broader
governance, that work must stop at that boundary for separate authorization.
It cannot infer authorization from this consequences section.

Planning only: once §16's effectiveness requirements are satisfied and separately
authorized for implementation, Slice 2 is expected to need controller-side ordinary/
terminal parsing, exclusive same-parent promotion with no replacement, T1/T2
authentication, restart recovery, synchronization barriers, and final recheck.
The intended implementation boundary remains `src/orev3/execution/runtime.py`
and `tests/execution/test_phase3b_worker_boundaries.py`, consuming existing
helpers read-only where sufficient. This is not authorization to edit them;
no necessary additional production-file modification is established by this
document. An implementation-discovered boundary conflict requires separate
resolution, not a fallback that weakens the protocol.

Future Slice-2 verification obligations (not tests executed by this document):

- ordinary orphan drains to lease-only; promotion requires every authentication
  precondition and preserves source/root/lease identity;
- no replacement, destination collision, no alternate-ID retry, and same-ID
  ordinary/terminal coexistence rejection;
- worker cannot mint terminal state or mutate structural namespace authority;
- crashes before and around promotion; fresh T1 restart; T1 contention,
  malformed lease, and unexpected extra content rejection;
- required parent durability failure blocks lease unlink; crash after unlink;
  T2 empty restart and unexpected-content rejection;
- wrong terminal mode/UID; symlink, hard-link, special-file, duplicate-inode,
  escaping/substituted identity rejection;
- terminal removal before/after parent durability, recovered namespace
  classification, and final recheck before success/admission;
- ordinary missing lease remains fail closed and pre-lease initialization
  remains distinct from terminal cleanup;
- published objects remain untouched; no new numeric/accounting category;
- existing frozen Slice-1 reservation regressions remain exact.

## 15. Explicit non-authorizations

This clarification does NOT authorize:

- Stage 3C Slice 2 implementation, Stage 3C completion, or changes to Slice 1;
- operational reservation integration or activation of RSS/watchdog machinery;
- production Experiment-005 adapter or registry adoption;
- Source S;
- readiness candidate/evidence/E/R;
- Experiment-005 execution;
- outcome/provider/backend authority;
- Paper Miner production authority;
- governed-host acceptance;
- final numeric-envelope adoption;
- wallet functionality or wallet funding;
- transaction construction/signing/submission;
- capital allocation; or
- real SOL activity or production mining.

No filesystem convention becomes scientific or numeric authority. Numeric
mode stays `BOUNDED_STREAMING_MEASUREMENT_CANDIDATE`.

## 16. Adoption record, effectiveness, and precedence

The exact independently reviewed candidate was:

- Path: `docs/research/governance/rq003-stage3c-recovery-permission-clarification-candidate.md`
- Byte count: 46845
- SHA-256: `65fa1a244e2a9f1178c273de33871c3194b986abcaf4d442db678292961744b8`
- Review disposition: **RECOVERY GOVERNANCE CORRECTED CANDIDATE REVIEW PASSED —
  EXPLICIT ADOPTION MAY BE CONSIDERED**

That independent review covered modes, ownership, ordinary and terminal grammar,
promotion preconditions, crash convergence, durability ordering, worker/controller
trust boundary, publication separation, and compatibility with controlling §§9
and 10.1. The subsequent explicit user adoption authorization permits this
in-place status/authority edit only, with no substantive recovery-rule change.

Document status is now ADOPTED CLARIFICATION. Git effectiveness remains pending.
Consistent with the repository's prospective clarification adoption practice,
this supplement becomes effective only after a separately authorized adoption
commit is pushed and independently live-remote verified. This edit performs
none of those Git actions and establishes no new remote-backed continuation
anchor.

The adopted identity (path, byte count, SHA-256) is reported externally, together
with the controlling path/SHA-256 from §1, review disposition, and supplemental
scope. The document does not embed its own hash as a purported fixed point.
Before effectiveness, independent verification MUST authenticate the adopted
bytes and status-only diff, repository/Git authority, protected identities,
reconciled mutable boundary, and exact authorized commit/push boundary.

At effectiveness, these rules supplement §9's otherwise-undefined private
recovery mode/owner/grammar predicate and its associated creation/partial-state
interpretation, plus the single `cleanup-<32 lowercase hex>` terminal state
and its necessary exclusive promotion/authentication/durability semantics.
No other persistent proof/state is added. Unrelated controlling requirements
remain in force without supersession. A substantive conflict requires separate
resolution, not automatic precedence for this file.

Adoption, commit, push, and independent live-remote verification remain distinct
transitions. Adoption alone does not authorize implementation or any downstream
activity listed above. Slice 2 remains blocked until this supplement is effective,
its adopted identity is independently authenticated, and implementation receives
separate explicit authorization.
