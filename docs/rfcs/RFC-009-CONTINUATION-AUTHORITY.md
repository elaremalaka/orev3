# RFC-009 — Minimal continuation authority

RFC-009 permits one interrupted, non-empty RFC-008 ledger to resume under one
explicitly approved successor release. It does not mutate the original
authorization or rebind historical rows.

The authority is a strict, immutable JSON document committed as the direct Git
child of the successor RFC-008 release-approval commit. That release approval
must itself be the direct child of the implementation commit. The document is
bound to the original authorization, ledger instance and canonical path,
starting count and last opportunity, exact ledger continuity digest, successor
release, implementation diff, and frozen experimental semantics.

Activation is one-shot. It appends epoch 2 to
`collection_release_epochs`; epoch 1 records the original RFC-008 authority.
The table permits only these two epochs and rejects updates and deletes. No new
database, mutable continuation state, event system, or successor chain exists.

The operator surface is:

```text
orev3.rfc008.cli preflight-continuation ... --continuation-approval PATH
orev3.rfc008.cli activate-continuation ... --continuation-approval PATH \
  --authorization-token RFC009_CONTINUATION_ACTIVATION_AUTHORIZED
orev3.rfc008.cli start --recovery --continuation-approval PATH ...
```

Preflight is read-only. Activation requires no active session, verifies the
frozen prefix and Git topology, and appends the immutable epoch. Recovery uses
the existing RFC-008 supervision, writer lease, session, startup handshake, and
authorization lifecycle. Ordinary launch cannot consume continuation authority.
