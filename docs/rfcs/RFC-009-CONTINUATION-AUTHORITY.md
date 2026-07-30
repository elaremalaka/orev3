# RFC-009 — Minimal continuation authority

RFC-009 permits an interrupted, non-empty RFC-008 ledger to resume through a
linear chain of explicitly approved successor releases. Each transition is
one-shot. It does not mutate the original authorization, an earlier transition
approval, an activated release epoch, or any historical collection row.

Each authority is a strict, immutable JSON document committed as the direct
Git child of its successor RFC-008 release-approval commit. That release
approval must itself be the direct child of the implementation commit. The
document is bound to the original authorization, ledger instance and canonical
path, starting count and last opportunity, exact ledger continuity digest,
immediate predecessor epoch and authority, predecessor and successor releases,
implementation diff, and frozen experimental semantics.

Activation is one-shot per transition. Epoch 1 records the original RFC-008
authority and the legacy epoch-2 record remains in
`collection_release_epochs`. Existing schema-7 successor records remain in
`collection_release_successor_epochs`; new epoch-3-and-later transitions are
appended to `collection_release_transition_epochs`. All three histories reject
updates and deletes. The combined history must be contiguous, unique, acyclic,
and linear; each successor names exactly the immediately preceding epoch and
authority. No new database, mutable continuation state, or event system exists.

An activated epoch normally owns the half-open opportunity interval from its
start sequence to the next epoch's start sequence. If an activated epoch
commits no opportunity before a separately approved successor is activated,
the successor may explicitly supersede that empty epoch. Successful activation
is the atomic governance event that ends the predecessor authority interval
and starts the successor authority interval. Exactly one operational authority
therefore governs at every instant, with neither a gap nor dual authority.
Consecutive activated epochs may have the same prospective opportunity
boundary only for this explicit empty-epoch supersession. The predecessor's
opportunity interval is empty, the successor owns the boundary onward, and
opportunity ownership never overlaps. Neither the predecessor nor any
historical opportunity is revoked, deleted, rewritten, or reassigned.

The operator surface is:

```text
orev3.rfc008.cli issue-continuation-approval ... \
  --continuation-approval \
  docs/research/rfc009/rfc008_continuation_approval_v1.json
# Later transitions use:
# docs/research/rfc009/rfc008_continuation_approval_epoch_N.json
orev3.rfc008.cli preflight-continuation ... --continuation-approval PATH
orev3.rfc008.cli activate-continuation ... --continuation-approval PATH \
  --authorization-token RFC009_CONTINUATION_ACTIVATION_AUTHORIZED
orev3.rfc008.cli start --recovery --continuation-approval PATH ...
```

Issuance is read-only except for atomically creating the epoch-specific
canonical approval document and refuses overwrite. It validates the committed
successor release, original authorization, exact non-empty interrupted ledger,
complete predecessor chain, semantic compatibility, canonical opportunity
sequence, last identity, session absence, and writer-lease absence. The
successor release must include the highest activated ledger release in its
validated Git approval ancestry. Approved intermediate releases that never
governed the ledger remain part of that audit ancestry but do not become ledger
epochs. The continuation UUID is deterministically derived from the immutable
approval fields, including the activated predecessor relationship; `created_at`
is the committed successor approval timestamp. Reissuing identical inputs
therefore produces identical bytes.

Preflight is read-only. Activation requires no active session, open collector
run, or active writer lease; verifies the frozen prefix, predecessor chain, and
Git topology; and appends exactly the next immutable epoch. Equal prospective
boundaries fail closed unless the immediate predecessor is proven empty.
Non-empty predecessors require a strictly later boundary. An activated
approval cannot be replayed, and an earlier approval cannot authorize recovery
after a later epoch is active. Recovery therefore recognizes only the highest
activated release epoch while historical epochs remain authoritative for their
sequence ranges. Collector-run records bind each new run to that governing
epoch and authority, allowing failed recovery attempts and all authority and
opportunity intervals to be reconstructed deterministically. Recovery uses
the existing RFC-008 supervision, writer lease, session, startup handshake,
and authorization lifecycle. Ordinary launch cannot consume continuation
authority.

Schema migration 7 is additive. It leaves legacy epochs 1 and 2 byte-for-byte
unchanged and adds only the successor-epoch table and its immutable chain
guards. A migrated epoch-2 ledger has identical authority and recovery behavior
until a separately issued, reviewed, committed, preflighted, and activated
epoch-3 approval exists.

Schema migration 8 is also additive. It does not rewrite any schema-7 authority
record. It adds the immutable transition history needed to distinguish ordinary
successors from explicit empty-epoch supersessions, permits a shared
prospective boundary only for the latter, and preserves the same activation
and recovery behavior until another transition is explicitly approved and
activated.
