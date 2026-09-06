# Stage 3C category-attribution adopted clarification

## 1. Status and authority

**ADOPTED CLARIFICATION — GIT EFFECTIVENESS PENDING — NO IMPLEMENTATION AUTHORITY.**

Following exact-byte independent review and explicit user authorization, this
status edit adopts the reviewed clarification. All MUST/MUST NOT statements below
become effective only after the separately authorized one-path commit, push and
independent live-remote verification described in §9. This edit alone establishes
no Git effectiveness or implementation authority.

Controlling authority:

- Path: `docs/research/governance/rq003-experiment-005-bounded-streaming-source-processing-prerequisite-v1.md`
- [Controlling governance](rq003-experiment-005-bounded-streaming-source-processing-prerequisite-v1.md)
- SHA-256: `ce09153fc98145f3fa318a9c7e8dd563afbf4b64496e64535b27c49c93af90e3`

Incorporated recovery authority:

- Path: `docs/research/governance/rq003-stage3c-recovery-permission-clarification-candidate.md`
- [Adopted recovery clarification](rq003-stage3c-recovery-permission-clarification-candidate.md)
- SHA-256: `7df413610a54adcacb06f5c01dc43b7ce2c04c5244922519871d745c0395f716`
- Remote-backed adoption commit: `045c041453d232e1288e6031fc528d61f8989caa`

Upon Git effectiveness, this adopted document supplements ONLY category attribution under controlling
§§9 and 9.1. It does not supersede aggregate accounting, publication authority,
recovery grammar, permission/ownership rules, or unrelated requirements. Conflicts
require separate resolution rather than automatic precedence for this clarification.
The objective remains an ORE miner eventually trustworthy with real SOL.

## 2. Exact gap and preserved facts

Controlling §9 defines full logical-length charging, reserve-before-growth and
publication, independent simultaneous candidate charges, and deletion/publication
release conditions. Section 9.1 enumerates five categories and requires controller-
owned confined paths and descriptor-derived observations. It does not exhaustively
partition object roles across those categories. A worker-produced projection can
also be a reconstruction candidate; producer identity alone cannot decide its class.

The measurement-mode disk schedule expressly includes request and stdout/stderr
file payloads. These are not zero-charge metadata. Lease and directories have zero
logical file length; socket frames are not disk charge. The schedule's existing
maxima are an admission envelope, not a replacement for actual logical observations.

The adopted recovery grammar permits confined regular descendants for inventory,
not arbitrary new output categories. This clarification creates no payload permission,
new numeric value, sixth reservation category, persistent binding file, journal,
ledger, or resume mechanism. Checked arithmetic, conservative outstanding allowances,
all lease rules, and terminal cleanup remain unchanged.

Compatibility evidence, not authority: current `runtime.py` creates the request
at the exact operation-root filename and leaves reservation descriptor binding to
future integration. `evidence_preparation.py` retains two projection candidates for
comparison and then retains one for publication. `dataset_validation.py` and
`filesystem_capability.py` can copy a retained projection into a publication
temporary. The copy and original coexist. Existing helper placement or release
ordering does not authorize future Stage-3 integration by itself.

## 3. Options and decision

| Option | Mapping principle | Consequences |
| --- | --- | --- |
| Fixed controller-bound role | Bind each object at creation to its authenticated production role; reconstruction candidates and separate publication copies have distinct roles | No transfer or persistent category state; writer identity does not override role; fits the governed two-candidate comparison and retained-original publication lifecycle |
| Fixed semantic projection attribution | Put both initial projection candidates and publication copies in projection_publication; reserve reconstruction_growth for other reconstructions | Deterministic if explicitly adopted, but makes the same governed comparison mechanism switch accounting classification according to output semantics rather than its creation role |
| Phase-based transfer | Start in worker/reconstruction category, then move charge at publication preparation | Needs debit/credit ordering, failure retention and restart interpretation; no existing lifecycle requires this transfer |

Select fixed controller-bound role attribution. The two independently generated
projection candidates are reconstruction work under controlling §8 and remain
charged together under §9. A distinct publication copy is publication work.
Keeping these roles fixed follows the actual coexistence of objects without a
new transfer event. Generic producer-based classification applies only after the
specific roles below have been excluded. This is the adopted policy choice resolving
the gap, not a claim that category names already imposed this mapping.

## 4. Exhaustive role mapping

The controller MUST apply this table to every otherwise-authorized charge-bearing
regular object before growth. A row does not authorize creation of an object or
expand the measurement schedule. File length means full logical length, with
existing outstanding/uncertain reservation treatment additionally preserved.

| Authenticated creation role | Fixed reservation category | Scope and precedence |
| --- | --- | --- |
| Source snapshot copy, including its source-publication temporary | snapshot_growth | Declared source bytes copied under controlling §3; includes source publication regardless of shared helper/directory names |
| Separate projection-publication copy/temporary | projection_publication | A new object populated from a projection for governed publication; excludes the retained original candidate |
| Projection candidate, including both independently generated comparison candidates | reconstruction_growth | Applies from initial candidate creation, including when a worker writes it; subsequent selection for publication does not reclassify it |
| Other already-authorized reconstruction candidate | reconstruction_growth | Includes independently generated reconstruction outputs; this row does not authorize additional reconstruction artifacts |
| Exact bounded-bootstrap-request.json | controller_temporary_growth | Controller-created request at the sole authorized operation-root location; count actual bytes |
| Already-authorized stdout capture or stderr capture | worker_output_growth | Applies even when a controller performs capture writes; count each file separately; no new capture mechanism is authorized |
| Other already-authorized controller-private temporary | controller_temporary_growth | Generic residual role only after all specific roles above have been excluded |
| Other already-authorized general worker output | worker_output_growth | Generic residual role only after all specific roles above have been excluded |

These rows exhaust the permitted charge-bearing roles for attribution. An object
that cannot be authenticated as one of them MUST NOT be assigned a convenient
fallback category. Additional legitimate roles require clarification before growth.
An arbitrary grammar-valid filename is not proof of an authorized role.

The zero/non-disk cases are not additional reservation categories:

- Lease: governed zero logical length, not a container for category metadata.
- Structural and nested directories, including terminal cleanup names: zero
  logical file length; no directory-entry charge is introduced.
- Pipe/socket bytes: no disk charge unless materialized in an already-authorized
  file, which then receives the applicable file category.
- Pre-existing independently authenticated immutable published snapshot/projection
  objects: existing zero operation charge, under separate publication authority.
- Shared coordination.lock: existing coordination metadata outside an operation's
  payload inventory; no growing payload or new zero-charge file exception is
  authorized here. This document does not alter its existing structural treatment.

## 5. Binding, overlap and fixed lifetime

Attribution is explicit controller binding constrained by existing structural and
capability authority. It is not a directory-name lookup. The four private directories
remain controller/, worker/, snapshot-publication/, and reconstruction/; their
permitted descendants and exact request location remain unchanged. This clarification
adds no filename, required relocation, directory, or exception to their grammar.

Under the existing coordination authority, the controller MUST establish a binding
between the operation, authenticated object descriptor/identity, authorized creation
role and exactly one table category. Bind before the first growth reservation/write;
a newly opened empty object still requires existing mode/UID/confinement authentication
before use. Existing nonempty objects cannot enter the ledger as zero: their actual
size and applicable existing reservations must be included before further growth.
If this cannot be authenticated, admission/growth fails closed.

The role derives from the controller's authorized creation operation, never from a
worker claim, filename, file contents, requested wire category, or later destination.
Source-copy and publication-copy roles are established by the authenticated input
and purpose of the copy operation. Initial generation/comparison is a candidate role,
not a publication-copy role. Capturing stdout/stderr is a capture role regardless
of who issues the write. The request role uses the exact governed request identity.
Generic controller/worker roles apply only to otherwise-authorized residual output.
Contradictory creation-role evidence fails closed; precedence cannot cure a conflict.

A worker-produced projection or reconstruction candidate therefore receives only
reconstruction_growth. A retained candidate later read for publication keeps that
binding. Only a separately created publication object receives projection_publication.
The controller MUST reject requests whose category does not match the controlled
write target/role. The path-free wire remains unchanged. An acknowledgment cannot
be spent on another object/category outside its controller-authorized write binding.

Each category observation MUST account for all currently chargeable objects bound
to that category, using authenticated descriptor sizes and checked arithmetic.
An object MUST appear in exactly one live category inventory. Identity substitution,
a duplicate binding, unsupported role, or inability to observe the required state
fails closed. No worker-supplied total substitutes for those observations.

Binding is fixed throughout the object's private lifetime. Rename, semantic
immutability, completion, comparison, selection, or publication preparation MUST NOT
change it. No cross-category transfer is proposed. Copying creates a distinct object
with its own creation role; releasing a completed object is not a category transfer.
Binding is controller-memory authority for the live operation, not persistent resume
state. Controller death does not authorize a successor to resume the live operation.

## 6. Simultaneous representations, links and release

Distinct simultaneously retained objects/inodes MUST remain separately charged even
when their bytes, hashes or scientific identities match. Both projection comparison
candidates are charged in reconstruction_growth. During publication copying, the
retained candidate remains there while the separate copy accumulates charge in
projection_publication. Source-publication copies use snapshot_growth instead.
No content-based deduplication of private charges is authorized.

Only inside the separately governed publication protocol, adding a name for the same
authenticated publication inode does not create a second logical object or second
category binding. It also does not reduce the creator's existing charge. This is
accounting interpretation only: it does not authorize hard links in ordinary private
inventory or relax the adopted single-link/duplicate-inode recovery rejection rules.
Linked or duplicate private crash residue continues to fail recovery closed where
existing governance requires it; it is not repaired by counting the inode once.

Release MUST apply only to the representation whose existing governed proof is
complete: verified deletion or successful atomic publication/handoff. A returned
pathname, link success alone, matching content, or a worker success claim is not
sufficient proof. Publishing a copy MUST NOT release its retained private original.
A losing dedup temporary remains charged until the winning target is authenticated
and the losing temporary's deletion is verified. Concurrent authenticated users of
an already-published object retain the existing zero-charge rule.

Failed or incomplete publication confers no release by itself. Preserve charge for
remaining private objects and existing uncertain allowances until the applicable
release proof completes. This clarification neither changes publication sequencing nor
implements publication/dedup; in particular it does not bless current helper behavior
where that behavior differs from controlling release or confinement requirements.

## 7. Partial writes and recovery

Reserve-before-growth, same-category short-write reconciliation, single-use matching
acknowledgments, checked totals and conservative uncertain retention remain controlling.
Partial candidate/request/capture/copy files keep their fixed category. A short write
is not permission to release unused allowance outside the existing next same-category
request or verified orderly EOF rule. Uncertain completion preserves the governed
greater-of-actual-and-acknowledged-prospective floor until failure/root removal as
required. No category reclassification can evade that floor.

Orphan recovery remains aggregate-only. After existing lease-based orphan authority
and complete confined validation, Slice 2 reconstructs the governed sum of unique
regular-file logical sizes before deletion, including request/capture bytes. It is
NOT required to reconstruct per-category totals, infer historical roles, or recover
lost in-memory reservations. This is cleanup, not scientific/operational resume.

A valid confined orphan payload whose historical live category is unavailable remains
eligible for existing aggregate cleanup; its size is not omitted. This differs from
an active operation attempting unattributable growth, which fails closed. Unsafe
modes/UIDs/links/types/grammar still reject before deletion. Live roots remain untouched.
The inherited lease continues to protect a surviving worker after controller death.
Terminal promotion occurs only after the existing lease-only drain and introduces
no category or charge. No persistent attribution metadata is necessary because no
per-category continuation survives controller death.

## 8. Adversarial disposition matrix

| Case | Exact proposed accounting disposition |
| --- | --- |
| Bootstrap request | controller_temporary_growth; actual file bytes, never zero metadata |
| Stdout capture | worker_output_growth; separate actual file length |
| Stderr capture | worker_output_growth; separate actual file length |
| Generic authorized controller temporary | controller_temporary_growth after specific-role exclusion |
| Generic authorized worker output | worker_output_growth after specific-role exclusion |
| Two simultaneous projection candidates | Both reconstruction_growth; sum their separate lengths |
| Two simultaneous reconstruction candidates | Both reconstruction_growth; retain first while second grows/compares |
| Worker-produced projection candidate | reconstruction_growth alone; producer does not override role |
| Publication copy while original remains | Copy projection_publication; original reconstruction_growth; retain both |
| Publication hard link | Same publication object/charge, no new charge merely for second name; no early release |
| Losing dedup temporary | Keep its fixed source/projection publication category until authenticated winner and verified deletion |
| Failed publication | Retain remaining object charges and applicable uncertainty floors |
| Partial write | Fixed category; only existing verified reconciliation may release allowance |
| Uncertain completion | Preserve existing prospective/actual conservative floor; no category escape |
| Orphan recovery | Existing aggregate inventory/delete; no category reconstruction or resume |
| Unattributable active object/growth | Fail closed; no generic fallback or zero omission |
| Overlapping producer/candidate/publication descriptions | Creation role wins; retained candidate never changes category; contradictory creation proof rejects |

## 9. Adoption record, effectiveness and implementation boundaries

After Git effectiveness and independent authentication of the adopted identity,
this supplies the role binding needed by Slice 3; a separate implementation
instruction is still required. It does
not activate the reservation core on real writes, require publication/dedup to be
implemented now, or change frozen Slices 1/2. Future tests should exercise the matrix,
category aggregate observations, substitution/duplicate binding rejection, wrong-wire-
category rejection, and unchanged uncertain-retention behavior. No tests or runtime
probes are authorized by creating this document.

The independently reviewed candidate identity was:

- Path: `docs/research/governance/rq003-stage3c-category-attribution-clarification-candidate.md`
- Bytes: 18457; lines: 257
- SHA-256: `52e91ee6c4a34a7df449afc75dfc2afeba43549a0c15fc6a024527fd01b58ac7`
- Review disposition: **STAGE 3C CATEGORY-ATTRIBUTION CANDIDATE REVIEW PASSED —
  EXPLICIT ADOPTION MAY BE CONSIDERED**

That independent review authenticated both governing identities and reviewed the
mapping, precedence, simultaneous-copy/release rules and aggregate-only recovery.
Subsequent explicit user authorization permits this status/authority adoption edit
only; the reviewed substantive attribution/accounting model remains unchanged.

Document status is ADOPTED CLARIFICATION; Git effectiveness remains pending.
Consistent with the established repository adoption procedure, effectiveness requires
a separately authorized commit containing only this path, normal push to the
configured tracking branch, and independent live-remote verification. This edit
performs none of those Git actions and creates no new remote-backed anchor.

Before effectiveness, independently authenticate the adopted bytes and status-only
diff, both governing identities, frozen Slice-2 identities, checkpoint/RFC identities,
repository/Git authority, index and reconciled mutable/write boundary. Report the
exact adopted byte count and SHA-256 externally; no self-hash fixed point is embedded.
Adoption, commit, push, remote verification and implementation authorization remain
distinct transitions. Slice 3 remains blocked until Git effectiveness and independent
adopted-identity authentication, followed by separate explicit implementation
authorization bound to that authority.

No Slice-3 implementation, publication/dedup implementation, changes to frozen slices,
RSS/watchdog activation, numeric-envelope adoption, governed-host acceptance,
Experiment-005 execution, adapter/registry/Source S, readiness candidate/evidence/E/R,
provider/backend/outcome authority, Paper Miner or other production authority, wallet,
transaction construction/signing/submission, capital allocation, or real SOL activity
is authorized. No comprehensive checkpoint is created or required by this clarification.
Numeric mode remains `BOUNDED_STREAMING_MEASUREMENT_CANDIDATE`; governed-host acceptance
remains deferred.
