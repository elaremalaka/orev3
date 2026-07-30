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
`collection_release_epochs`. Epoch 3 and later records are appended to
`collection_release_successor_epochs`. Both histories reject updates and
deletes. The combined history must be contiguous, unique, acyclic, and linear;
each successor names exactly the immediately preceding epoch and authority.
No new database, mutable continuation state, or event system exists.

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
successor release must directly supersede the active ledger release. The
continuation UUID is deterministically derived from the immutable approval
fields, including the predecessor relationship; `created_at` is the committed
successor approval timestamp. Reissuing identical inputs therefore produces
identical bytes.

Preflight is read-only. Activation requires no active session, verifies the
frozen prefix, predecessor chain, and Git topology, and appends exactly the
next immutable epoch. An activated approval cannot be replayed, and an earlier
approval cannot authorize recovery after a later epoch is active. Recovery
therefore recognizes only the highest activated release epoch while historical
epochs remain authoritative for their sequence ranges. It uses the existing
RFC-008 supervision, writer lease, session, startup handshake, and authorization
lifecycle. Ordinary launch cannot consume continuation authority.

Schema migration 7 is additive. It leaves legacy epochs 1 and 2 byte-for-byte
unchanged and adds only the successor-epoch table and its immutable chain
guards. A migrated epoch-2 ledger has identical authority and recovery behavior
until a separately issued, reviewed, committed, preflighted, and activated
epoch-3 approval exists.
