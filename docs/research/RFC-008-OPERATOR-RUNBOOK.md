# RFC-008 Paper Evaluation Operator Runbook

Status: **Corrected implementation reference; marker and collection are not
authorized**

Runbook contract version: `rfc008-operator-runbook-v8`

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
  --preserve-pid 48404 \
  --preserve-pid 48405 \
  --preserve-pid 78317 \
  --authorization-token RFC008_OPERATIONAL_RESOLVER_BURN_IN_AUTHORIZED
```

Operational evidence schema version 4 records complete per-round provenance,
normalized persisted attempt records, normalized operational request records,
and exact RPC counts by provider, method, response classification, and retry
status. Every real round must be read from both providers at finalized
commitment and must pass owner, PDA, returned identity, decoded round,
finalized-context, deployment-vector, accounting, and canonical-agreement
checks. Deployment and accounting pass counts are derived from per-round
evidence and must equal the authoritative success count. Attempt counts,
provider request references, account reads, genesis reads, retries, successful
responses, unavailable responses, malformed responses, failed responses, and
total RPC requests must all reconcile. Fixture calls are structurally excluded
from operational accounting. Fewer than five successes, duplicates, missing
attempts or requests, incomplete provenance, or any provider disagreement fail
closed.

The durable source boundary is authoritative structured evidence containing
the boundary round, source path, inode, byte offset, line number, source-record
SHA-256, source-record timestamp, and the distinct timestamp at which the
boundary was observed. The five operational rounds must be exactly
`boundary_round - 5` through `boundary_round - 1`.

The exact protected-process policy is observer PID `48404`, observer
caffeinate PID `48405`, and RFC-007 collector PID `78317`, each with its
approved role and sanitized command identity. Command hashes and observation
timestamps are captured before any provider request and checked again after
the isolated exercises. A missing, substituted, duplicated, absent, or changed
process fails the burn-in.

The same isolated ledger also performs separately reported controlled checks.
Restart/retry persists a pending fixture attempt, closes and reopens the ledger,
and then finalizes it. Deterministic jitter is a distinct result with tested
retry numbers, expected and recomputed delays, bounded-delay validation,
persisted schedule validation, and derivation version. Conflict injects a
non-authoritative disagreement and proves terminal overwrite refusal.
Quarantine uses a different controlled round identity, invokes the production
expiry transition with a controlled clock, reopens the ledger, and proves that
later resolution cannot silently overwrite quarantine. Restart/retry, conflict,
and quarantine identities cannot overlap the five real rounds; conflict and
quarantine must also be distinct. Fixture calls never count as operational RPC
calls or authoritative successes.

Every controlled-test pass flag is derived from its required subchecks and must
equal the separately serialized recomputed result. Conflict evidence requires
two retained provider provenance records, retained disagreement details,
persisted terminal conflict state, an attempted and refused overwrite, proof
that later success did not replace the conflict, and primary-analysis
ineligibility. Quarantine evidence requires controlled expiry, invocation of
the production quarantine transition, persisted terminal quarantine state, an
attempted and refused overwrite, proof that later success did not replace the
quarantine, and primary-analysis ineligibility. Marker preflight independently
checks these subfields; it does not trust the controlled pass flags alone.

Provider-provenance linkage failures are reported as
`rpc_attempt_reconciliation_failed` and `provider_provenance_invalid`.
Structurally present jitter evidence with failed deterministic, bounded-delay,
schedule, version, or retry-coverage checks is reported as
`jitter_test_failed`.

The CLI reports the real-round summary, RPC request accounting, attempt
reconciliation, restart, retry, jitter, conflict, quarantine, exact process
preservation, structured source boundary, and recomputed authoritative
capability separately. The command exits nonzero unless every operational,
restart, retry, jitter, conflict, quarantine, integrity, safety, and isolation
gate passes. Even a passing burn-in grants neither marker nor collection
authorization. Operational evidence is valid for 24 hours.

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
schema-v4 operational evidence, at least five distinct authoritative successes,
complete deployment and accounting validation, reconciled persisted
attempt/request history and RPC accounting, complete provider provenance,
distinct controlled conflict and quarantine identities, separate passing
restart, retry, jitter, conflict, and quarantine evidence, all three protected
processes, and a complete structured source boundary consistent with
deterministic round selection. It is not authorization.

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

Marker publication binds the immutable historical source boundary recorded in
the validated operational burn-in evidence. Append-only observer growth after
that boundary is expected and does not invalidate publication. The command
revalidates the exact historical path, inode, record-end offset, line, record
hash, round, record timestamp, and boundary-observation timestamp immediately
before atomic publication; mutation, truncation, replacement, or invalid
rotation of that record fails closed. The current observer cursor is recorded
separately only to seed future collection cursors. Marker publication remains
one-time and does not authorize or start collection.

### Lifecycle and cursor terminology

RFC-008 lifecycle checks are phase-specific:

* **Pre-marker:** marker, sidecar, production ledger family, collector,
  dataset, freeze, and analysis outputs are absent.
* **Post-marker, pre-collection:** one valid immutable marker and matching
  sidecar are present; the marker keeps collection authorization false; the
  production ledger family, collector, dataset, freeze, and analysis outputs
  remain absent.
* **Collection:** only a separately authorized run may create the production
  ledger or start the collector. Dataset, freeze, and analysis outputs remain
  subject to their later authorization boundaries.

The schema-v2 `runtime_source_*` fields are the immutable historical burn-in
eligibility boundary. For the published marker this remains round `346052`,
line `69558`, record-end offset `74568652`, and the approved record hash.
The `source_identities` values are later marker-publication cursors used to
seed collection and prevent replay. They may advance with normal observer
appends and are not required to equal the historical eligibility boundary.
They cannot redefine the eligible burn-in rounds or move collection seeding
backward before the historical boundary.

### Release-approval supersession

Post-marker validation accepts only the canonical RFC-008 release approval
schema. A refreshed approval must bind the exact implementation commit, the
immediately previous approval hash, the immutable marker pair, and every
frozen experiment, resolver, schema, CLI, runbook, and approval-manifest
identity. Historical approvals are retained by content hash so validation can
walk the ordered chain to the approval embedded in the immutable marker.
Every link must keep collection, live-action, wallet, and transaction
authorization false. Copied marker hashes alone never establish approval.

### Schema-2 approval field authority

The canonical active approval contract is
`docs/research/rfc008/schema2_approval_field_authority_v1.json`. It is
mechanically generated from `SCHEMA2_APPROVAL_FIELDS` in
`src/orev3/rfc008/approval_contract.py`; the same ordered registry drives
generation, duplicate-safe parsing, validation, documentation-consistency
tests, and exhaustive mutation tests.

The contract contains exactly 54 required leaf fields: 11 exact
release-bound fields, 17 derived release-bound fields, 17 policy-bound fields,
5 explicit authorization fields, and 4 informational fields. Every entry
declares its JSON type, applicability, validation source, structured failure
reason, canonical representation, and mutation policy. Active approvals reject
unknown top-level or nested fields and aliases. Duplicate JSON keys are
rejected before a mapping is created.

Informational fields are required and type/format checked, but their values do
not grant authority and valid alternatives do not invalidate an otherwise
valid approval. All other active fields are checked against their authoritative
release, evidence, marker, repository, configuration, schema, process, or
policy source. Missing, null, mistyped, or changed authoritative values fail
closed.

<!-- BEGIN GENERATED SCHEMA-2 APPROVAL FIELD AUTHORITY TABLE -->
| Field path | Authority class | Required | Validation source | Applicability | Mutation behavior |
|---|---|---:|---|---|---|
| `artifact_type` | `release_bound_exact` | yes | `constant` | `active_and_legacy` | `reject_mutation` |
| `schema_version` | `release_bound_exact` | yes | `constant` | `active_and_legacy` | `reject_mutation` |
| `rfc_identifier` | `release_bound_exact` | yes | `constant` | `active` | `reject_mutation` |
| `repository_branch` | `release_bound_exact` | yes | `git_branch` | `active` | `reject_mutation` |
| `status` | `release_bound_exact` | yes | `constant` | `active_and_legacy` | `reject_mutation` |
| `approved_implementation_commit` | `release_bound_derived` | yes | `git_approval_parent` | `active_and_legacy` | `reject_mutation` |
| `approval_commit_policy` | `policy_bound` | yes | `constant` | `active_and_legacy` | `reject_mutation` |
| `supersedes_release_implementation_approval_sha256` | `release_bound_derived` | yes | `git_parent_approval` | `active_and_legacy` | `reject_mutation` |
| `validated_production_marker_sha256` | `release_bound_derived` | yes | `marker_bytes` | `active_and_legacy` | `reject_mutation` |
| `validated_production_marker_sidecar_sha256` | `release_bound_derived` | yes | `marker_sidecar_bytes` | `active_and_legacy` | `reject_mutation` |
| `validated_production_marker_repository_commit` | `release_bound_derived` | yes | `marker_document` | `active_and_legacy` | `reject_mutation` |
| `validated_production_marker_release_approval_sha256` | `release_bound_derived` | yes | `marker_document` | `active_and_legacy` | `reject_mutation` |
| `validated_production_marker_collection_authorized` | `authorization` | yes | `marker_document_false` | `active_and_legacy` | `reject_mutation` |
| `validated_operational_burn_in_evidence_sha256` | `release_bound_derived` | yes | `burn_in_evidence_bytes` | `active_and_legacy` | `reject_mutation` |
| `validated_operational_burn_in_ledger_sha256` | `release_bound_derived` | yes | `burn_in_ledger_bytes` | `active_and_legacy` | `reject_mutation` |
| `validated_operational_burn_in_repository_commit` | `release_bound_derived` | yes | `burn_in_evidence_document` | `active_and_legacy` | `reject_mutation` |
| `frozen_approval_manifest_sha256` | `release_bound_derived` | yes | `approval_manifest_bytes` | `active_and_legacy` | `reject_mutation` |
| `configuration_fingerprint` | `release_bound_derived` | yes | `experiment_config` | `active_and_legacy` | `reject_mutation` |
| `candidate_configuration_sha256` | `release_bound_derived` | yes | `marker_document` | `active_and_legacy` | `reject_mutation` |
| `resolver_configuration_sha256` | `release_bound_derived` | yes | `resolver_config` | `active_and_legacy` | `reject_mutation` |
| `audit_version` | `policy_bound` | yes | `constant` | `active_and_legacy` | `reject_mutation` |
| `audit_correction_identifier` | `informational` | yes | `format_only` | `active_and_legacy` | `accept_valid_alternative` |
| `resolver_version` | `policy_bound` | yes | `resolver_config` | `active_and_legacy` | `reject_mutation` |
| `decoder_version` | `policy_bound` | yes | `resolver_config` | `active_and_legacy` | `reject_mutation` |
| `database_family` | `release_bound_exact` | yes | `constant` | `active_and_legacy` | `reject_mutation` |
| `database_schema_version` | `release_bound_exact` | yes | `constant` | `active_and_legacy` | `reject_mutation` |
| `migration_set_sha256` | `release_bound_derived` | yes | `migration_registry` | `active_and_legacy` | `reject_mutation` |
| `burn_in_evidence_schema_version` | `release_bound_exact` | yes | `constant` | `active_and_legacy` | `reject_mutation` |
| `marker_schema_version` | `release_bound_exact` | yes | `constant` | `active_and_legacy` | `reject_mutation` |
| `minimum_operational_sample_size` | `policy_bound` | yes | `constant` | `active_and_legacy` | `reject_mutation` |
| `protected_process_policy.48404.role` | `policy_bound` | yes | `protected_process_registry` | `active_and_legacy` | `reject_mutation` |
| `protected_process_policy.48404.sanitized_command_identity` | `policy_bound` | yes | `protected_process_registry` | `active_and_legacy` | `reject_mutation` |
| `protected_process_policy.48405.role` | `policy_bound` | yes | `protected_process_registry` | `active_and_legacy` | `reject_mutation` |
| `protected_process_policy.48405.sanitized_command_identity` | `policy_bound` | yes | `protected_process_registry` | `active_and_legacy` | `reject_mutation` |
| `protected_process_policy.78317.role` | `policy_bound` | yes | `protected_process_registry` | `active_and_legacy` | `reject_mutation` |
| `protected_process_policy.78317.sanitized_command_identity` | `policy_bound` | yes | `protected_process_registry` | `active_and_legacy` | `reject_mutation` |
| `cli_version` | `release_bound_exact` | yes | `constant` | `active_and_legacy` | `reject_mutation` |
| `cli_sha256` | `release_bound_derived` | yes | `cli_bytes` | `active_and_legacy` | `reject_mutation` |
| `runbook_version` | `release_bound_exact` | yes | `constant` | `active_and_legacy` | `reject_mutation` |
| `runbook_sha256` | `release_bound_derived` | yes | `runbook_bytes` | `active_and_legacy` | `reject_mutation` |
| `verification.focused_lifecycle_test_count` | `informational` | yes | `format_only` | `active_and_legacy` | `accept_valid_alternative` |
| `verification.rfc008_test_count` | `informational` | yes | `format_only` | `active_and_legacy` | `accept_valid_alternative` |
| `verification.full_test_count` | `informational` | yes | `format_only` | `active_and_legacy` | `accept_valid_alternative` |
| `verification.fixture_resolver_burn_in_required` | `policy_bound` | yes | `constant` | `active_and_legacy` | `reject_mutation` |
| `verification.operational_resolver_burn_in_required_before_marker` | `policy_bound` | yes | `constant` | `active_and_legacy` | `reject_mutation` |
| `verification.external_rpc_burn_in_performed` | `release_bound_derived` | yes | `burn_in_evidence_document` | `active_and_legacy` | `reject_mutation` |
| `authorization_boundary.implementation_authorized` | `policy_bound` | yes | `constant` | `active_and_legacy` | `reject_mutation` |
| `authorization_boundary.fixture_burn_in_authorized` | `policy_bound` | yes | `constant` | `active_and_legacy` | `reject_mutation` |
| `authorization_boundary.operational_rpc_burn_in_authorized` | `policy_bound` | yes | `constant` | `active_and_legacy` | `reject_mutation` |
| `authorization_boundary.marker_creation_authorized` | `policy_bound` | yes | `constant` | `active_and_legacy` | `reject_mutation` |
| `authorization_boundary.collection_authorized` | `authorization` | yes | `explicit_false` | `active_and_legacy` | `reject_mutation` |
| `authorization_boundary.wallet_access_authorized` | `authorization` | yes | `explicit_false` | `active_and_legacy` | `reject_mutation` |
| `authorization_boundary.live_action_authorized` | `authorization` | yes | `explicit_false` | `active_and_legacy` | `reject_mutation` |
| `authorization_boundary.transaction_authorized` | `authorization` | yes | `explicit_false` | `active` | `reject_mutation` |
<!-- END GENERATED SCHEMA-2 APPROVAL FIELD AUTHORITY TABLE -->

Schema-1 approvals are legacy compatibility records only. They are accepted
solely when reached by immutable SHA-256 links while walking a schema-2
approval chain to the approval embedded in the production marker. A schema-1
document is never accepted as the active release approval.

### Shared active release validation

`validate_active_release` is the single active acceptance entry point used by
marker preflight, lifecycle validation, collection preflight, collection
startup, and the CLI. Its immutable result includes the parsed approval and
hash plus schema, artifact, field-contract, derived-field, policy,
authorization, chain, and marker-binding verdicts. Callers may add lifecycle
or launch checks, but cannot suppress an active-release check.

All 17 derived fields are recomputed: implementation and predecessor from the
Git approval relationship; marker, sidecar, burn-in evidence, burn-in ledger,
approval manifest, CLI, and runbook from bytes; marker repository, marker
approval, candidate identity, and burn-in repository from their validated
documents; experiment and resolver identities from parsed configuration;
migrations from the ordered canonical migration registry with source bytes
also matched to the implementation commit; and operational RPC performance
from the validated burn-in evidence. A same-name substituted ledger, a
same-checkout CLI or runbook edit, or any migration-source edit fails closed.

Before any separately authorized collection start, run the read-only gate:

```bash
PYTHONPATH=src .venv/bin/python -m orev3.rfc008.cli preflight-collection \
  --config config/collection/rfc008_paper_v1.json \
  --resolver-config config/collection/rfc008_resolver_v1.json \
  --marker data/ledger/rfc008_marker_v1.json \
  --ledger data/ledger/rfc008_paper_ledger_v1.sqlite \
  --authorization data/ledger/rfc008_collection_authorization_v1.sqlite \
  --action launch \
  --repository-root . \
  --burn-in-evidence data/resolver/rfc008_operational_burn_in_v1.json \
  --release-approval docs/research/rfc008/release_implementation_approval_v1.json \
  --approval-manifest docs/research/rfc008/approval_manifest_v1.json
```

## 6. Future collection start

Collection requires a separately issued persisted authorization. Issuance is
itself the separately human-authorized operation; the command-line path merely
identifies the resulting SQLite evidence and is not a reusable secret:

```bash
PYTHONPATH=src .venv/bin/python -m orev3.rfc008.cli issue-collection-authorization \
  --config config/collection/rfc008_paper_v1.json \
  --resolver-config config/collection/rfc008_resolver_v1.json \
  --marker data/ledger/rfc008_marker_v1.json \
  --expected-marker-sha256-file data/ledger/rfc008_marker_v1.json.sha256 \
  --ledger data/ledger/rfc008_paper_ledger_v1.sqlite \
  --authorization data/ledger/rfc008_collection_authorization_v1.sqlite \
  --repository-root . \
  --burn-in-evidence data/resolver/rfc008_operational_burn_in_v1.json \
  --release-approval docs/research/rfc008/release_implementation_approval_v1.json \
  --approval-manifest docs/research/rfc008/approval_manifest_v1.json
```

Inspect the authorization read-only, initialize the bound ledger exactly once,
then rerun the collection preflight with `--action launch`:

```bash
PYTHONPATH=src .venv/bin/python -m orev3.rfc008.cli inspect-collection-authorization \
  --authorization data/ledger/rfc008_collection_authorization_v1.sqlite

PYTHONPATH=src .venv/bin/python -m orev3.rfc008.cli initialize-ledger \
  --config config/collection/rfc008_paper_v1.json \
  --resolver-config config/collection/rfc008_resolver_v1.json \
  --marker data/ledger/rfc008_marker_v1.json \
  --expected-marker-sha256-file data/ledger/rfc008_marker_v1.json.sha256 \
  --ledger data/ledger/rfc008_paper_ledger_v1.sqlite \
  --authorization data/ledger/rfc008_collection_authorization_v1.sqlite \
  --repository-root . \
  --burn-in-evidence data/resolver/rfc008_operational_burn_in_v1.json \
  --release-approval docs/research/rfc008/release_implementation_approval_v1.json \
  --approval-manifest docs/research/rfc008/approval_manifest_v1.json
```

Launch only after that preflight reports ready. Production collection uses the
repository-owned supervised interface; do not use `nohup`, shell `&`,
`disown`, `screen`, `tmux`, or another improvised wrapper:

```bash
PYTHONPATH=src .venv/bin/python -m orev3.rfc008.cli start \
  --config config/collection/rfc008_paper_v1.json \
  --marker data/ledger/rfc008_marker_v1.json \
  --expected-marker-sha256-file data/ledger/rfc008_marker_v1.json.sha256 \
  --ledger data/ledger/rfc008_paper_ledger_v1.sqlite \
  --authorization data/ledger/rfc008_collection_authorization_v1.sqlite
```

`start` performs the release and collection preflights, takes an exclusive
launch mutex, rejects authoritative active-session or writer-lease state, and
launches the existing `run` command with `start_new_session=True`, detached
stdin, deliberately closed file descriptors, a controlled environment, and
combined stdout/stderr at:

```text
data/ledger/rfc008_paper_ledger_v1.collector.log
```

It atomically publishes schema-1 supervision metadata at:

```text
data/ledger/rfc008_paper_ledger_v1.supervision.json
```

Launch success is reported only after the child remains alive, the exact
process-start identity matches, the writer lease is held by that PID, the
authorization and ledger name the same session, and the corresponding open
`collector_runs` row exists. The metadata contains no RPC URL or environment
value. A child that exits before the handshake, a timeout, PID reuse, an
active writer, a duplicate session, or inconsistent authorization/ledger
state fails closed.

An inactive supervision record is recoverable as stale only when the process,
authorization, ledger session, open run, and advisory writer lease all agree
that no collector is active. The next authorized `start` records the prior
launch identity and state in `stale_recovery`; it does not rewrite the
authorization or ledger. An old writer-lock file is not manually removed:
the existing advisory-lock acquisition decides whether a writer is active and
updates the PID only after exclusive acquisition succeeds.

The authorization is release-, marker-, path-, paper-mode-, and
600-opportunity-bound. Initialization and launch consumption are
transactional. A restart uses the same command plus `--recovery`; it is
accepted only for the same active authorization and ledger after the exclusive
writer lease is obtained. Source cursors, count, pending queue, retry state,
attempts, conflicts, and accepted outcomes persist. Opportunity 600
transactionally completes collection and causes a successful collector exit;
opportunity 601 cannot be committed. Completion does not invoke freeze,
dataset generation, analysis, or deployment.

The authorization database and paper ledger are separate SQLite databases.
Cross-database same-transaction completion is deliberately not part of the
RFC-008 contract. Opportunity 600, the canonical snapshot and arm decisions,
sequence, count, last identity, completed state, and completion timestamp are
atomic within the ledger. That completed ledger immediately prevents
opportunity 601 and is authoritative over temporarily stale `active`
authorization metadata.

Authorization completion and session cleanup are mandatory and idempotent.
Normal `finish_run()` completes both. If a process stops after the ledger
commit but before cleanup, `preflight-collection --action recovery` reports
`collection_completed: true` and `reconciliation_required: true`. Running the
same bound collection command with `--recovery` acquires the writer lease,
revalidates the ledger and authorization binding, clears or finalizes the
stale session, reconciles authorization to `completed`, starts no collector,
and exits completed. Repeating recovery remains an idempotent completed exit.
A copied, path-mismatched, instance-mismatched, release-mismatched, or
authorization-mismatched ledger is rejected before reconciliation.

## 7. Collection monitoring

```bash
PYTHONPATH=src .venv/bin/python -m orev3.rfc008.cli status \
  --config config/collection/rfc008_paper_v1.json \
  --marker data/ledger/rfc008_marker_v1.json \
  --expected-marker-sha256-file data/ledger/rfc008_marker_v1.json.sha256 \
  --ledger data/ledger/rfc008_paper_ledger_v1.sqlite \
  --authorization data/ledger/rfc008_collection_authorization_v1.sqlite
```

Monitor integrity, primary and sensitivity provenance, pending/conflicted/
quarantined outcomes, unusable denominator and rate, duplicates, safety
counters, and stopping caps. No interim efficacy analysis is allowed.

## 8. Safe stop and restart

Send SIGINT only to the RFC-008 collector. Do not signal the observer,
RFC-007 collector, or caffeinate wrapper. Confirm the RFC-008 writer lease is
released, run status, and restart with supervised `start --recovery` using the exact
authorization, marker, hash, configuration, resolver configuration, provider
identities, and ledger. A completed ledger exits without creating another
session. If authorization remains `active` because the process stopped after
the opportunity-600 ledger commit, this recovery invocation performs mandatory
completion reconciliation and stale-session cleanup before exiting. It never
reopens the completed collection. Repeating the same recovery is safe and
remains completed.

The status command remains read-only and reports the recorded and current Git
identities, metadata and log paths, process liveness and process-start
identity, authorization/session binding, canonical and stored counts, arm
decisions, open and latest run records, advisory writer-lease state,
reconciliation requirements, and process/ledger agreement. On normal target
completion, the child records `completed` supervision state after the ledger
reaches exactly 600, the session and authorization close, and the lease is
released. On an unexpected post-session exit it records `interrupted`;
operators must inspect status and use the existing separately authorized
recovery path. Supervision never automatically restarts a failed collector.

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
