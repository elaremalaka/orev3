# RFC-008 Paper Evaluation Operator Runbook

Status: **Corrected implementation reference; marker and collection are not
authorized**

All commands run from `/Users/anisbaker/Documents/orev3`. Production commands
below are future procedures and were not executed during implementation.

## 1. Boundaries that must not be confused

The frozen candidate-training boundary is rounds `342132` through `342570`.
It controls candidate selection only and is never passed to marker creation.

The runtime holdout boundary is the last complete observer record immediately
before marker publication. `preflight-marker` derives its round, source path,
inode, byte offset, line number, record SHA-256, and timestamp automatically.
`create-marker` derives it again and refuses a cursor race.

## 2. Deterministic fixture resolver burn-in

This isolated mode uses local providers and cannot establish operational
provider readiness:

```bash
PYTHONPATH=src .venv/bin/python -m orev3.rfc008.cli resolver-burn-in \
  --config config/collection/rfc008_paper_v1.json \
  --resolver-config config/collection/rfc008_resolver_v1.json \
  --ledger /tmp/rfc008_fixture_burn_in.sqlite \
  --output /tmp/rfc008_fixture_burn_in.json \
  --mode fixture \
  --control-round-id 900001
```

The fixture ledger and evidence are never holdout inputs.

## 3. Future operational read-only resolver burn-in

This step requires separate authorization and two independent provider URLs in
`ORE_RECOVERY_PRIMARY_RPC_URL` and `ORE_RECOVERY_SECONDARY_RPC_URL`. URLs and
credentials are never printed or stored. It deterministically selects exactly
the latest five completed rounds strictly before the durable observer boundary
captured at burn-in start: `boundary_round - 5` through
`boundary_round - 1`. Selection is bounded; unavailable rounds cause failure
instead of a broader historical search. These rounds are non-production,
non-holdout, and ineligible for the 600-round target.

```bash
PYTHONPATH=src .venv/bin/python -m orev3.rfc008.cli resolver-burn-in \
  --config config/collection/rfc008_paper_v1.json \
  --resolver-config config/collection/rfc008_resolver_v1.json \
  --ledger data/resolver/rfc008_operational_burn_in_v1.sqlite \
  --output data/resolver/rfc008_operational_burn_in_v1.json \
  --mode operational \
  --sample-size 5 \
  --release-approval docs/research/rfc008/release_implementation_approval_v1.json \
  --repository-root . \
  --authorization-token RFC008_OPERATIONAL_RESOLVER_BURN_IN_AUTHORIZED
```

Operational evidence schema version 2 records complete per-round provenance
and exact RPC counts by provider and method. Every real round must be read from
both providers at finalized commitment and must pass owner, PDA, returned
identity, decoded round, finalized-context, deployment-vector, accounting, and
canonical-agreement checks. Fewer than five successes, duplicates, missing
counts, incomplete provenance, or any provider disagreement fail closed.

The same isolated ledger also performs four separately reported controlled
checks. Restart/retry persists a pending fixture attempt, closes and reopens the
ledger, validates deterministic jitter, and then finalizes it. Conflict injects
a non-authoritative disagreement and proves terminal overwrite refusal.
Quarantine creates a different unresolved fixture round, invokes the production
expiry transition with a controlled clock, reopens the ledger, and proves that
later resolution cannot silently overwrite quarantine. Fixture calls never
count as operational RPC calls or authoritative successes.

The command exits nonzero unless every operational, restart, retry/jitter,
conflict, quarantine, integrity, safety, and isolation gate passes. Even a
passing burn-in grants neither marker nor collection authorization.
Operational evidence is valid for 24 hours.

## 4. Read-only release preflight

```bash
PYTHONPATH=src .venv/bin/python -m orev3.rfc008.cli preflight-marker \
  --config config/collection/rfc008_paper_v1.json \
  --resolver-config config/collection/rfc008_resolver_v1.json \
  --burn-in-evidence data/resolver/rfc008_operational_burn_in_v1.json \
  --release-approval docs/research/rfc008/release_implementation_approval_v1.json \
  --marker data/ledger/rfc008_marker_v1.json \
  --ledger data/ledger/rfc008_paper_ledger_v1.sqlite \
  --approval-manifest docs/research/rfc008/approval_manifest_v1.json \
  --repository-root . \
  --expected-branch research/rfc-007-paper-collection-burn-in
```

`ready: true` requires the approved HEAD policy, completely clean worktree,
absent production artifacts, valid frozen hashes, recent hash-validated
schema-v2 operational evidence, at least five distinct authoritative successes,
internally consistent RPC accounting, complete provider provenance, separate
passing restart/retry, conflict, and quarantine evidence, and a current runtime
source boundary. It is not authorization.

## 5. Future marker creation

After separate human authorization:

```bash
PYTHONPATH=src .venv/bin/python -m orev3.rfc008.cli create-marker \
  --config config/collection/rfc008_paper_v1.json \
  --resolver-config config/collection/rfc008_resolver_v1.json \
  --burn-in-evidence data/resolver/rfc008_operational_burn_in_v1.json \
  --release-approval docs/research/rfc008/release_implementation_approval_v1.json \
  --marker data/ledger/rfc008_marker_v1.json \
  --ledger data/ledger/rfc008_paper_ledger_v1.sqlite \
  --approval-manifest docs/research/rfc008/approval_manifest_v1.json \
  --repository-root . \
  --expected-branch research/rfc-007-paper-collection-burn-in \
  --authorization-token RFC008_MARKER_CREATION_AUTHORIZED
```

The marker and checksum sidecar are staged, fsynced, validated, and published
as a fail-safe pair. The marker becomes visible last. No ledger is created.

## 6. Future collection start

Collection requires separate authorization and the same operational provider
environment:

```bash
PYTHONPATH=src .venv/bin/python -m orev3.rfc008.cli run \
  --config config/collection/rfc008_paper_v1.json \
  --resolver-config config/collection/rfc008_resolver_v1.json \
  --marker data/ledger/rfc008_marker_v1.json \
  --expected-marker-sha256-file data/ledger/rfc008_marker_v1.json.sha256 \
  --ledger data/ledger/rfc008_paper_ledger_v1.sqlite \
  --create-new-ledger \
  --authorization-token RFC008_HOLDOUT_COLLECTION_AUTHORIZED
```

Restarts omit `--create-new-ledger`. The writer lease, source cursors,
pending queue, retry count, next retry time, attempts, conflicts, and accepted
outcomes persist.

## 7. Collection monitoring

```bash
PYTHONPATH=src .venv/bin/python -m orev3.rfc008.cli status \
  --config config/collection/rfc008_paper_v1.json \
  --marker data/ledger/rfc008_marker_v1.json \
  --expected-marker-sha256-file data/ledger/rfc008_marker_v1.json.sha256 \
  --ledger data/ledger/rfc008_paper_ledger_v1.sqlite
```

Monitor integrity, primary and sensitivity provenance, pending/conflicted/
quarantined outcomes, unusable denominator and rate, duplicates, safety
counters, and stopping caps. No interim efficacy analysis is allowed.

## 8. Safe stop and restart

Send SIGINT only to the RFC-008 collector. Do not signal the observer,
RFC-007 collector, or caffeinate wrapper. Confirm the RFC-008 writer lease is
released, run status, and restart with the exact marker, hash, configuration,
resolver configuration, provider identities, and ledger.

## 9. Future authorized final freeze

After the stopping rule is reached and the writer is stopped:

```bash
PYTHONPATH=src .venv/bin/python -m orev3.rfc008.cli final-freeze \
  --config config/collection/rfc008_paper_v1.json \
  --marker data/ledger/rfc008_marker_v1.json \
  --expected-marker-sha256-file data/ledger/rfc008_marker_v1.json.sha256 \
  --ledger data/ledger/rfc008_paper_ledger_v1.sqlite \
  --output data/freeze/rfc008_final_freeze_v1.json \
  --stop-reason AUTHORIZED_TERMINAL_REASON \
  --authorization-token RFC008_FINAL_FREEZE_AUTHORIZED
```

Freeze refuses an active writer, pending outcomes, integrity failure, marker
or configuration drift, and an existing different freeze. Persistent write
guards make the ledger immutable after the freeze.

## 10. Dataset generation from the freeze

```bash
PYTHONPATH=src .venv/bin/python -m orev3.rfc008.cli build-dataset \
  --config config/collection/rfc008_paper_v1.json \
  --marker data/ledger/rfc008_marker_v1.json \
  --expected-marker-sha256-file data/ledger/rfc008_marker_v1.json.sha256 \
  --ledger data/ledger/rfc008_paper_ledger_v1.sqlite \
  --freeze data/freeze/rfc008_final_freeze_v1.json \
  --expected-freeze-sha256-file data/freeze/rfc008_final_freeze_v1.json.sha256 \
  --output data/analysis/rfc008_round_dataset_v1
```

The dataset manifest carries the complete frozen experiment summary. Recovered
outcomes remain sensitivity-only.

## 11. Formal analysis authorization

```bash
PYTHONPATH=src .venv/bin/python -m orev3.rfc008.cli analyze \
  --config config/collection/rfc008_paper_v1.json \
  --dataset data/analysis/rfc008_round_dataset_v1 \
  --expected-dataset-manifest-sha256-file data/analysis/rfc008_round_dataset_v1/manifest.json.sha256 \
  --output data/analysis/rfc008_results_v1.json \
  --authorization-token RFC008_FORMAL_ANALYSIS_AUTHORIZED
```

Analysis refuses a missing or changed manifest and derives started rounds,
missingness, safety, cap, provenance, and final-freeze inputs from frozen
evidence. It never substitutes optimistic defaults.

## Safety boundary

RFC-008 has no wallet loader, signer, transaction builder, submitter, deploy
instruction, or claim instruction. The resolver performs finalized read-only
account acquisition only. Paper success does not authorize live testing.
