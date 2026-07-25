# RFC-006 — Participant Economic Ledger and Passive Data Collection

## 1. Executive summary

RFC-006 adds a deterministic, observational participant-economic ledger. It
stores point-in-time opportunities, strategy decisions, deployment intent,
read-only transaction observations, wallet snapshots, rewards, claims, and
reconciliation results without exposing any transaction-building, signing,
submission, claim, private-key, or balance-changing path.

The storage format is schema-versioned SQLite. Generated databases, reports,
exports, wallet public keys, transaction signatures, and participant activity
remain ignored.

Historical reconciliation does **not** resolve the evidence gap identified by
RFC-005. A point-in-time snapshot of the four available raw observer files
contained 135,273 lines: 135,272 valid observer records and one malformed line.
Every valid observation was imported, but the source logs contain no
participant decision, deployment, transaction, fee, wallet, reward, or claim
records. Therefore:

- fully reconciled historical opportunities: 0 of 135,272 (0%);
- observation coverage: 100%;
- decision, transaction, fee, wallet, reward, and claim coverage: 0%; and
- RFC-005 cannot be rerun with realized participant economics.

No live deployment is justified.

## 2. Motivation from RFC-005

RFC-005 found sometimes-positive reconstructed price-taking results but
chronological instability, weak paired evidence, only 22 directly observed OOS
rounds, zero OOS Motherlodes, unavailable base ORE, assumed fees, and no
participant wallet ledger. RFC-006 addresses the collection and accounting
boundary rather than adding a model or strategy search.

## 3. Security boundary

RFC-006 is read-only:

- no keypair or seed-phrase import;
- no signer import;
- no transaction builder;
- no transaction or claim submission;
- no private-key persistence;
- no balance mutation;
- no live-miner integration; and
- no bypass of existing safety boundaries.

The CLI has explicit tripwire flags for transaction building, signing,
submission, and claims. Requesting any of them fails before observation or
storage I/O. The RPC adapter has a fixed allowlist containing only
`getTransaction`, `getSignatureStatuses`, `getBalance`, and
`getTokenAccountBalance`. Existing board observation continues to use only
`getSlot`, `getAccountInfo`, and `getMultipleAccounts`.

Repository-wide inspection found no existing wallet loader, keypair reader,
signer, transaction builder, transaction submission helper, claim helper, or
live miner. `solders` is used only for public keys, signatures, and account
address derivation/validation.

## 4. Repository sources discovered

| Source | Type and schema | Timestamp semantics | Authority | Expected uniqueness | Missing fields / caveats |
|---|---|---|---|---|---|
| `data/raw/observer_*.jsonl` | Observer schemas 1 and 2 | Local UTC capture time plus confirmed RPC slot | Direct local record of direct RPC account observations | Source path, line, and content digest; opportunity is round plus within-round observation index | No participant decision, wallet, transaction, fee, return, base ORE, or claim |
| `logs/collector_events_*.jsonl` | Operational events without a version field | Local UTC event time | Direct local log | Source path and line | Session/transition/error metadata only; not participant economics |
| `data/derived/round_lifecycles_v1.jsonl` | Lifecycle schema 1, 439 rounds | References raw observation times and slots | Derived; outcome provenance is observed or enriched | Round ID | Final protocol outcome, not participant wallet accounting |
| `data/derived/round_lifecycles_v2.jsonl` | Lifecycle schema 1, 1,317 rounds | Same as above | Derived | Round ID | Same limitation |
| RFC-004 prediction artifacts | CSV/JSON research output | Historical OOS decision coordinates | Reconstructed model evaluation | Fold/strategy/opportunity | Not persisted participant decisions or live rank vectors |
| RFC-005 economic artifacts | CSV/JSON research output | Historical counterfactual coordinates | Reconstructed/configured assumptions | Strategy/scenario/opportunity | Not wallet-realized evidence |

Observer timestamps are local capture timestamps, not block time. RPC slot
regressions are preserved. Clock skew relative to validator block time is
unknown because transaction/block metadata was not captured.

The raw `observer_2026-07-25.jsonl` file was still being appended during final
verification. Both idempotence runs therefore used the same immutable
point-in-time copy of all four raw files. Source files were not changed.

## 5. Event model

Schema version 1 defines append-friendly observation, decision, transaction,
wallet, reward, claim, and reconciliation event types. Every event has:

`event_id`, `event_type`, `event_time`, `observed_at`, `source`,
`source_record_id`, `run_id`, `session_id`, nullable lifecycle identifiers,
strict-JSON payload, and `schema_version`.

Transaction lifecycle events exist for importing historical facts. RFC-006
does not itself create, sign, or submit a transaction.

## 6. Identifier design

- `opportunity_id`: deterministic UUIDv5 of `(round_id, observation_index)`.
- `event_id`: deterministic UUIDv5 of event type, source, and source record.
- `decision_id` and `deployment_intent_id`: deterministic UUIDv5 of their
  immutable inputs.
- `source_record_id`: deterministic UUIDv5 including source, line, and SHA-256
  content digest.
- `run_id` and `session_id`: either externally supplied, deterministic for an
  import batch, or generated UUIDs for a new live session.
- wallet public keys and transaction/claim signatures: externally assigned
  Solana identifiers.

No Python object hash or process-dependent identifier is used. A frozen source
set re-imports idempotently. Backfilling an older observation into a round can
change later within-round observation indices; such backfills must be imported
as a new versioned source batch rather than silently rewriting an existing
ledger.

## 7. Data authority hierarchy

The ledger exposes these provenance classes:

1. `direct_wallet_observation`
2. `direct_rpc_observation`
3. `direct_program_event`
4. `direct_local_log`
5. `reconstructed`
6. `inferred`
7. `configured_assumption`
8. `unavailable`

Economic values can carry source identifier, observation time, confidence,
finality, and provenance. Missing direct values remain null; assumptions do
not replace them.

## 8. Storage design

SQLite schema version 1 contains metadata, source records, events,
opportunities, decisions, deployments, transactions, wallet snapshots,
rewards, claims, and reconciliation tables. Primary keys, unique
`(round_id, observation_index)` opportunities, source-event uniqueness, and
foreign keys provide idempotence and referential checks.

SQLite was chosen from the Python standard library. It adds no dependency and
provides transactional imports that JSONL alone would not.

The verification ledger is approximately 496 MB for 135,272 full snapshot
events; the database plus plain, pseudonymized, and reproducibility exports is
approximately 709 MB. This is acceptable for the research checkpoint but is a
storage-cost warning for continuous collection. A later migration may
normalize repeated board payloads or add compression without weakening source
traceability.

## 9. Observation mode

`orev3.ledger.cli observe --mode passive` accepts a recorded snapshot or makes
one read-only observation through the existing observer. It records the board,
round, treasury, opportunity, and an explicit passive/no-participation
decision. It creates no transaction event.

Fixture-backed and one-shot behavior is tested. Continuous unattended use has
not yet been operationally burn-in tested.

## 10. Paper-decision mode

Paper mode records selected squares, exact intended allocation, participation,
decision latency, strategy identity, and version. It never creates a
transaction. Frozen RFC-004 artifacts do not contain a serialized inference
pipeline or complete live ranking vectors, so model-ranked paper decisions are
rejected rather than fabricated. The capture interface is ready for a later
read-only inference adapter.

## 11. Historical import

The JSONL importer:

- validates observer schemas 1 and 2;
- tolerates and counts malformed or partial records;
- preserves source references;
- never mutates source files;
- supports dry-run;
- uses uniqueness constraints; and
- reports imported, duplicate, partial, malformed, and failed counts.

Collector event and derived outcome logs were inventoried but not forced into
participant opportunities because they do not contain supported participant
identifiers or economic facts.

## 12. RPC observation

The generic read-only parser supports transaction slot, block time, error,
fee payer, total fee, explicitly available priority fee, SOL balances, token
balances, program IDs, parsed instruction types, logs, and account keys.

Confirmation alone is not treated as protocol success. Where an ORE program ID
and success marker are configured, both must be present. Generic parsing stays
separate from protocol interpretation.

Standard historical observer logs contain no transaction signature or RPC
transaction metadata, so this path was verified with recorded fixtures only.

## 13. Wallet-delta accounting

Before/after wallet snapshots preserve raw SOL and ORE deltas. Known deployment,
return, and fee amounts are reconciled separately. Unexplained movements are
classified as funding, withdrawal, unrelated transfer, ambiguous, or manual
review rather than automatically assigned to mining.

## 14. External funding treatment

The tracked configuration uses a documented default threshold of 0.1 SOL for
an unexplained positive balance jump. Direct transaction counterparty evidence
takes precedence. Raw deltas remain preserved and mining-attributed deltas
exclude identified funding and withdrawals.

No historical wallet snapshots exist, so RFC-006 found zero classifiable
funding events and zero unexplained wallet deltas—not evidence that neither
occurred.

## 15. Reward observation

Reward records distinguish gross SOL return, net SOL before fees, base ORE,
Motherlode ORE, and total ORE. Values may be directly observed or explicitly
reconstructed. Negative ORE is prohibited.

## 16. Base-versus-Motherlode accounting

When only total ORE is observable, base and Motherlode components remain null.
They are never inferred from a total. Historical board logs expose round-level
Motherlode state, but not participant Motherlode receipts. They expose no base
ORE receipt.

## 17. Claim attribution

The ledger supports:

- direct references, high confidence;
- uniquely supported balance difference, medium confidence;
- FIFO fallback, low confidence; and
- proportional fallback, low confidence.

Attributed and unattributed amounts must sum exactly to the claim. Fallback
methods are labeled and never presented as direct fact.

## 18. Reconciliation states

Supported states include complete, complete no-participation, missing
transaction/fee/reward/claim/wallet snapshot, ambiguous wallet or claim
attribution, failed validation, and manual review. Confirmation alone cannot
make an opportunity complete.

## 19. Completeness scoring

Observation, decision, transaction, fee, wallet, reward, and claim components
are exposed separately as values from zero to one. The aggregate is their
transparent mean; reports retain component and missing-field counts.

## 20. Privacy and artifact hygiene

`data/ledger/`, versioned participant SQLite files, CSV exports, and JSON
reports are ignored. User wallet data and transaction history must not be
committed.

Exports may replace wallet public keys and fee payers with deterministic
SHA-256-derived labels within an export. This is pseudonymization, not
anonymization; timestamps, signatures, and activity can remain identifying.
Secret-like fields are rejected recursively before serialization.

## 21. Historical reconciliation results

Point-in-time source snapshot:

- source lines: 135,273;
- valid/imported records: 135,272;
- unique observation opportunities: 135,272;
- unique rounds: 1,744;
- malformed records: 1;
- partial records: 0;
- unknown/failed schemas: 0;
- decisions: 0;
- deployment intents: 0;
- submitted, confirmed, or failed transactions: 0;
- wallet snapshots: 0;
- fee observations: 0;
- reward observations: 0;
- claim observations: 0;
- complete opportunities: 0;
- partial opportunities: 135,272;
- ambiguous opportunities: 0;
- unmatched transactions or claims: 0;
- external funding events: 0 observable;
- unexplained wallet deltas: 0 observable;
- earliest timestamp: `2026-07-23T04:47:51.776566Z`; and
- latest timestamp: `2026-07-25T09:16:48.593498Z`.

All partial records are `partial_missing_transaction`; they also explicitly
list missing decision, reward, wallet snapshot, and claim. Fee coverage cannot
be evaluated without a submitted transaction.

## 22. Coverage by source

| Source snapshot | Valid records |
|---|---:|
| Observer validation file | 3,328 |
| July 23 overnight observer | 33,956 |
| July 24 observer | 64,760 |
| July 25 point-in-time observer | 33,228 |
| **Total** | **135,272** |

There is one deterministic import run and one historical-import session.
Wallet-label coverage is empty because no wallet was captured.

## 23. Missing-field analysis

Every imported opportunity lacks a linked participant decision, deployment
transaction, wallet snapshot, participant return, reward, and claim. No source
contains directly observed fees, priority fees, external funding evidence, or
participant base/Motherlode ORE.

## 24. Reproducibility

The second import of the frozen source snapshot:

- imported zero new records;
- identified all 135,272 valid records as duplicates; and
- left the SQLite SHA-256 byte-identical at
  `da1f4f28b0b524f559a29a8980bd0ebfe0baf351cb65f3d8459f9d4be91fe282`.

Repeated reports and pseudonymized exports were byte-identical. All JSON
artifacts passed strict parsing with NaN and Infinity rejected.

## 25. Limitations

- The available historical logs are board observations, not participant logs.
- A current raw observer file is actively changing and must be snapshotted for
  reproducibility.
- Live transaction observation is fixture-tested but not network-validated.
- Priority fee is reported only when directly exposed; it is not guessed.
- The ORE-specific transaction success marker needs validation against recorded
  participant transactions.
- Continuous passive operation has not completed a burn-in period.
- Model paper decisions need a leakage-safe serialized inference adapter.
- Pseudonymization does not anonymize transaction activity.

## 26. Blockers

Realized economic evaluation remains blocked by absent participant decision
logs, transaction signatures and protocol outcomes, direct fees, paired wallet
snapshots, participant SOL returns, base ORE, participant Motherlode ORE,
claimable balances, and claim attribution.

## 27. Direct answers and decision

1. Every imported observation can be uniquely identified within a versioned,
   immutable source batch.
2. The schema can link every decision to an opportunity; historical coverage
   is 0%.
3. Deployment intent is distinct from transaction submission.
4. Submission is distinct from RPC confirmation and protocol landing.
5. Total transaction fees can be measured from RPC metadata when signatures
   exist; historical coverage is 0%.
6. Priority fees can be measured only when directly exposed or separately
   proven; current historical coverage is 0%.
7. External funding can be separated when snapshots and/or transaction
   counterparties exist; current history cannot do so.
8. SOL returns cannot currently be directly attributed to opportunities.
9. Base ORE cannot currently be directly measured.
10. Round Motherlode is observed, but participant Motherlode ORE is not.
11. Claims can be attributed with labeled methods; historical coverage is 0%.
12. Fully reconciled historical opportunities: 0%.
13. The largest ambiguity is the complete absence of participant-level
    transaction, wallet, reward, and claim records.
14. Historical data is not sufficient to rerun RFC-005 with realized
    participant economics.
15. Passive capture is fixture-tested and safe for a limited read-only burn-in,
    but not yet validated for continuous unattended use.
16. Generic paper-decision logging is ready; model-ranked continuous paper
    decisions are blocked on a serialized inference adapter.
17. No live deployment is justified.
18. Before economic reevaluation, collect at least 1,000 participated
    opportunities across at least four chronological blocks, with at least 250
    per block, and meet all of: 95% opportunity-decision linkage, 95% submitted
    transaction identification, 95% direct fee observation, 95% landed/failed
    classification, 90% wallet-delta reconciliation, 90% reward attribution,
    explicit unclaimed rewards, excluded external funding, explicit base ORE
    availability, directly observed Motherlode treatment, deterministic
    re-import, and zero private-key or submission use. Motherlode-specific
    conclusions additionally require at least 10 directly observed participant
    Motherlode receipts; otherwise that analysis must remain unavailable.

RFC-006 approves no live activity.

## 28. Recommended next gate

Run a time-bounded passive/paper data-collection burn-in using a dedicated
public wallet address only, recorded transaction fixtures or read-only RPC,
paired wallet snapshots, and explicit claimable/claimed ORE observations.
Validate the ORE program’s transaction and reward semantics against direct
records. Continue paper simulation. Repeat realized economic evaluation only
after the stated volume and completeness thresholds are met.
