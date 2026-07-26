# RFC-008 Paper Evaluation Operator Runbook

Status: **Implementation reference; collection not authorized**

This runbook describes future commands. None of the marker, ledger,
collection, dataset, or analysis commands below were executed while RFC-008
was implemented.

All commands run from `/Users/anisbaker/Documents/orev3`.

## 1. Technical preflight

The read-only preflight verifies the approved manifest, frozen configuration,
branch, clean tracked worktree, available marker paths, observer source files,
and paper-only safety boundary:

```bash
PYTHONPATH=src .venv/bin/python -m orev3.rfc008.cli preflight-marker \
  --config config/collection/rfc008_paper_v1.json \
  --marker data/ledger/rfc008_marker_v1.json \
  --approval-manifest docs/research/rfc008/approval_manifest_v1.json \
  --repository-root . \
  --expected-branch research/rfc-007-paper-collection-burn-in
```

`ready: true` is technical readiness only. It is not authorization.

## 2. Future marker creation

After separate human authorization, use exactly:

```bash
PYTHONPATH=src .venv/bin/python -m orev3.rfc008.cli create-marker \
  --config config/collection/rfc008_paper_v1.json \
  --marker data/ledger/rfc008_marker_v1.json \
  --approval-manifest docs/research/rfc008/approval_manifest_v1.json \
  --repository-root . \
  --expected-branch research/rfc-007-paper-collection-burn-in \
  --latest-preholdout-round-id 342570 \
  --authorization-token RFC008_MARKER_CREATION_AUTHORIZED
```

This creates the immutable marker and
`data/ledger/rfc008_marker_v1.json.sha256`. It does not create a ledger or
start collection. Existing output paths are refused.

## 3. Dry-run validation

Use only temporary fixture paths:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/rfc008
```

Do not point a dry run at an RFC-007 ledger, production marker, or observer
output.

## 4. Future collection start

After marker review and separate collection authorization, use exactly:

```bash
PYTHONPATH=src .venv/bin/python -m orev3.rfc008.cli run \
  --config config/collection/rfc008_paper_v1.json \
  --marker data/ledger/rfc008_marker_v1.json \
  --expected-marker-sha256-file data/ledger/rfc008_marker_v1.json.sha256 \
  --ledger data/ledger/rfc008_paper_ledger_v1.sqlite \
  --create-new-ledger \
  --authorization-token RFC008_HOLDOUT_COLLECTION_AUTHORIZED
```

The first run refuses an existing ledger. Restarts use the same command
without `--create-new-ledger`. A writer lease prevents two collectors from
targeting the ledger.

## 5. Status monitoring

```bash
PYTHONPATH=src .venv/bin/python -m orev3.rfc008.cli status \
  --config config/collection/rfc008_paper_v1.json \
  --marker data/ledger/rfc008_marker_v1.json \
  --expected-marker-sha256-file data/ledger/rfc008_marker_v1.json.sha256 \
  --ledger data/ledger/rfc008_paper_ledger_v1.sqlite
```

Review integrity, configuration, marker verification, primary-analyzable
rounds, started rounds, pending/conflicted/quarantined outcomes, unusable
rate, duplicates, safety counters, and caps. `collection_ready` is technical
health and does not authorize a start.

## 6. Safe stop and restart recovery

Send SIGINT only to the RFC-008 collector process. Do not signal the observer,
RFC-007 collector, or caffeinate wrapper. Wait for the collector to exit and
confirm the writer lease is released. Verify status, then restart with the
same config, marker, hash sidecar, and ledger, omitting
`--create-new-ledger`.

The source cursor, one-snapshot uniqueness, pending-outcome queue, resolver
state, and accounting identities persist in SQLite. A transition is committed
to the pending queue before resolution. No transition infers a winner.

## 7. Final freeze

Stop only after 600 directly observed primary-analyzable rounds or a frozen
terminal boundary. Record the final status JSON, ledger SHA-256, marker
SHA-256, configuration fingerprint, repository commit, and source cursors.
Any conflict, marker drift, configuration drift, integrity failure, live
action, or unusable rate above 5% requires human review.

## 8. Dataset generation

Only after final-freeze authorization:

```bash
PYTHONPATH=src .venv/bin/python -m orev3.rfc008.cli build-dataset \
  --config config/collection/rfc008_paper_v1.json \
  --marker data/ledger/rfc008_marker_v1.json \
  --expected-marker-sha256-file data/ledger/rfc008_marker_v1.json.sha256 \
  --ledger data/ledger/rfc008_paper_ledger_v1.sqlite \
  --output data/analysis/rfc008_round_dataset_v1
```

Generation requires exactly 600 primary rounds, one shared snapshot per
round, five arms, complete accounting, no conflicts, and no non-terminal
outcomes. Recovered rounds are written only to the labeled sensitivity file.

## 9. Analysis authorization

Formal analysis remains separately authorized:

```bash
PYTHONPATH=src .venv/bin/python -m orev3.rfc008.cli analyze \
  --config config/collection/rfc008_paper_v1.json \
  --dataset data/analysis/rfc008_round_dataset_v1 \
  --output data/analysis/rfc008_results_v1.json \
  --authorization-token RFC008_FORMAL_ANALYSIS_AUTHORIZED
```

The command validates dataset hashes before running the locked paired
McNemar, paired bootstrap, economic randomization, ROI, and decision engine.
Recovered provenance is descriptive sensitivity evidence only.

## Safety boundary

RFC-008 contains no signer, wallet loader, transaction builder, submitter,
deploy instruction, claim instruction, or RPC recovery adapter. Paper success
does not authorize live testing.
