# RFC-007 — Continuous Paper Collection and Ledger Burn-In

## 1. Executive summary

RFC-007 implements a continuous, restartable, paper-only collection service
that reads the existing observer’s append-only JSONL output and writes to a
separate RFC-007 SQLite ledger. It links:

`observation → opportunity → paper decision → deployment intent → outcome → reconstructed paper accounting → reconciliation`

The historical replay burn-in processed 100 consecutive eligible
opportunities and passed Gate A with:

- 100% opportunity-to-decision linkage;
- 100% finalized-outcome linkage;
- zero duplicate opportunities or decisions;
- zero malformed source records;
- zero source corruption;
- zero database-lock failures;
- complete paper-accounting provenance;
- a forced close/reopen at opportunity 50; and
- zero live actions.

This is a `historical_replay_burn_in`, not a real-time result. No indefinite
collector was launched. Real-time Gate A remains required before Gate B
collection begins.

## 2. RFC-006 motivation

RFC-006 found 135,272 valid historical board observations but zero historical
participant decision, transaction, fee, wallet, reward, or claim coverage.
RFC-007 starts collecting linked paper lifecycles without claiming that paper
intent is a submitted transaction or realized participant economics.

## 3. Observer noninterference design

The production observer remained active as PID `48404`, running
`python -m orev3.observer.collect` with a `caffeinate` child. Its writer uses
`O_APPEND`, writes one newline-terminated record with a single `os.write`, and
closes immediately.

RFC-007:

- opens observer JSONL only in binary read mode;
- advances only past complete newline-terminated records;
- leaves a partial final line pending;
- never locks, truncates, rotates, renames, or writes observer output;
- never changes observer code, cadence, configuration, or environment;
- never signals, restarts, or stops the observer; and
- writes only to separate ignored RFC-007 paths.

No persistent exclusive lock was found on the active observer files. Concurrent
read behavior is safe for this append pattern.

## 4. Security boundary

RFC-007 has no wallet loader, seed-phrase reader, keypair, signer, transaction
builder, transaction submission, claim invocation, balance mutation, or
mutating RPC method. Configuration and CLI tripwires reject building, signing,
submitting, and claiming before collection I/O.

Paper deployment records have status
`paper_intent_only_never_submitted`, no wallet, and no transaction signature.

## 5. Source formats discovered

The collection source is Observer JSONL schema 1 or 2:

- UTC observer timestamp;
- confirmed RPC slot;
- board round/start/end state;
- treasury Motherlode state; and
- 25-element miner, deployment, and reward arrays.

Final outcomes come from versioned lifecycle JSONL. They retain `observed` or
`enriched` outcome provenance and are used only after the contemporaneous paper
decision exists.

## 6. Incremental ingestion

The tailer reads from a byte offset in bounded batches. It handles clean
append, incomplete final lines, malformed lines, duplicate content,
out-of-order timestamps, source growth, rotation to a new path, truncation,
and inode replacement.

Truncation or replacement raises a manual-review error. The cursor is never
silently reset.

## 7. Cursor design

Each source cursor persists:

- deterministic source ID;
- path and source type;
- byte offset and line number;
- last record ID;
- last observer timestamp;
- last ingestion timestamp;
- file size and inode; and
- schema version.

Cursor and records commit in the same SQLite transaction. An interrupted batch
therefore commits both or neither.

Existing files default to `live_start_mode=end` at a newly declared real-time
burn-in start. Files discovered later, including UTC rotation files, start at
the beginning.

## 8. Opportunity construction

The canonical key is `(round_id, observation_index)`. The array-based observer
format provides an implicit, deterministic square index from 0 through 24.
All miner, deployed-lamport, and reward arrays must contain exactly 25
nonnegative values. Board and round IDs must agree.

Incomplete observations are persisted separately with a reason and expiry
status. Missing squares are never fabricated.

## 9. Paper strategy configuration

The frozen burn-in configuration is:

- strategy: `existing_least_crowded`;
- version: `1.0.0`;
- ranking: ascending miner count, then ascending square index;
- squares: top four;
- allocation: equal;
- intended deployment: 50,000 lamports; and
- assumed deploy and claim fees: 5,000 lamports each.

Configuration SHA-256:

`11118d1f69328abc523a022a681733a49c95b3582c1c24496988d2dd14dfb81d`

This matches the repository’s existing least-crowded top-four baseline. It was
not tuned during RFC-007.

## 10. Strategy limitations

RFC-007 also supports least miner count, least deployed lamports, lowest miner
share, and deterministic seeded random rankings. Ties resolve by ascending
square index.

RFC-004 model ranking is unavailable. The repository has neither a serialized
live inference pipeline nor complete live-compatible ranking vectors. RFC-007
records `strategy_unavailable` and does not reconstruct model behavior from
winner ranks.

## 11. Paper decision schema

Paper decisions include source and decision times, latency, selected squares,
ranking order and scores where available, square count, allocation rule,
intended lamports, exact square allocation, participation, configuration hash,
and collector version.

Decision and deployment-intent IDs are deterministic. Duplicate decisions are
rejected by both primary and opportunity uniqueness constraints.

## 12. Outcome linking

Outcomes link deterministically by round ID and include winner, final time,
source authority, all 25 final deployments, total winnings, Motherlode, base
ORE availability, and source reference.

Duplicate substantive outcomes are counted. Conflicts are reported. A
correction creates a new version with `correction_of`; it never silently
overwrites a finalized outcome. Missing winners, deployments, unmatched
rounds, and late outcomes remain explicit.

## 13. Paper accounting

RFC-007 reuses RFC-005’s price-taking mechanics:

`selected winner allocation × total_winnings ÷ final winning-square deployment`

It stores gross return, net SOL before fees, configured deploy/claim fees, net
SOL after assumed fees, base ORE, Motherlode ORE, and total ORE separately.

## 14. Provenance

Paper returns and Motherlode allocation are `reconstructed`; fees are
`configured_assumption`; base ORE and total ORE remain `unavailable` when base
ORE is absent. Every record is classified
`reconstructed_paper_not_wallet_realized`.

## 15. Restart and resume

SIGINT and SIGTERM set a clean-stop flag. The replay deliberately closed the
database after 50 opportunities, reopened it, resumed from the durable cursor,
and reached 100 without gaps or duplicates.

Unit tests also cover cursor restart, transaction rollback after an interrupted
batch, and source records appended after restart.

## 16. SQLite concurrency

The dedicated ledger uses:

- WAL journal mode;
- `synchronous=NORMAL`;
- configurable busy timeout, default 5 seconds;
- transaction-bounded batches;
- foreign keys and uniqueness constraints;
- integrity checks; and
- explicit checkpoint/compaction guidance.

A transient write lock was released during the configured busy timeout and the
collector recovered. Simulated interrupted work rolled back and left
`PRAGMA integrity_check` equal to `ok`.

## 17. Duplicate-process protection

An adjacent `*.writer.lock` file uses nonblocking OS `flock`. A second writer
targeting the same ledger fails immediately and safely. The lock is released
on normal close or process exit.

## 18. Health metrics

Health output includes source counts, duplicates, malformed records, cursor
lag, opportunity and decision counts, outcome/reconciliation counts, database
size, optional peak memory, processing latency, and last-success timestamps.
JSON is strict and runtime-dependent fields are removed from deterministic
exports.

## 19. Disk growth

The normalized replay ledger is 933,888 bytes for 100 opportunities, or
9,338.88 bytes per opportunity:

| Opportunities | Estimated ledger size |
|---:|---:|
| 1,000 | 9,338,880 bytes (~9.3 MB) |
| 10,000 | 93,388,799 bytes (~93.4 MB) |
| 100,000 | 933,887,999 bytes (~934 MB) |

Peak memory observed in the verification process was approximately 35.5 MB.
Batch size bounds active record memory.

Verbose raw payload retention is configurable and disabled for burn-in.
Nothing is deleted automatically. Archive is explicit and non-destructive.
Compaction requires a manual archive and a stopped RFC-007 collector; it never
requires stopping the production observer.

## 20. Replay burn-in results

- source: July 23 overnight Observer JSONL;
- consecutive opportunities: 100;
- completed paper decisions: 100;
- linked outcomes: 100;
- completed paper reconciliations: 100;
- duplicates: 0;
- malformed records: 0;
- expired partials: 0;
- linkage: 100%;
- outcome linkage: 100%;
- integrity: `ok`; and
- live actions: 0.

The first 100 observations span two finalized rounds. No rows were
cherry-picked after evaluation; collection began at source offset zero and
stopped after the first 100 eligible observations.

## 21. Real-time burn-in status

Real-time collection was not launched. Real-time Gate A is incomplete. The
service is prepared for a separate-terminal burn-in, but replay success is not
presented as real-time reliability evidence.

## 22. Gate A evaluation

`historical_replay_burn_in`: **PASS**

`real_time_burn_in`: **NOT STARTED**

## 23. Gate B readiness

Gate B is not yet open because real-time Gate A has not passed. The collector
is ready to begin an unattended real-time burn-in, subject to the documented
launcher and health monitoring. A 1,000-opportunity research collection may
start only after 100 consecutive real-time opportunities pass Gate A.

## 24. Chronological block design

The tracked configuration freezes four 250-opportunity blocks:

| Block | Opportunity indices | Target | Use |
|---|---:|---:|---|
| block_1 | 0–249 | 250 | research |
| block_2 | 250–499 | 250 | research |
| block_3 | 500–749 | 250 | research |
| block_4 | 750–999 | 250 | report-only |

All blocks share the same configuration hash and collector version. Boundaries
must not move based on results.

## 25. Observer impact assessment

RFC-007 modified no observer source or active observer output. It issued no
process signal and changed no observer environment or cadence. Concurrent
verification observed natural append growth while the pre-existing byte prefix
remained the integrity boundary.

## 26. Reproducibility

Two clean replay ledgers are byte-identical:

`4be1aa3a6d5acbea6a4ce498778a2f4533f7e01dffab1885d5d87a25e340a7dc`

All ten deterministic exports are byte-identical between runs. Strict JSON
rejects NaN and Infinity. Deterministic gzip uses an epoch modification time.

## 27. Limitations

- Real-time Gate A has not run.
- Outcome linking during replay uses historical finalized lifecycle records.
- No wallet-realized data is collected in paper mode.
- Base ORE remains unavailable.
- Fees remain configured assumptions.
- Model-ranked paper collection is unavailable.
- Disk estimates are linear projections from a 100-opportunity sample.
- Long-duration memory, rotation, RPC latency, and operating-system behavior
  still require real-time burn-in evidence.

## 28. Blockers

RFC-005 rerun remains blocked on realized participant transactions, direct
fees, wallet deltas, returned SOL, base/Motherlode ORE receipts, and claims.

Any controlled-live RFC additionally requires completed real-time Gate A,
completed 1,000-opportunity paper collection across the frozen blocks,
predeclared economic evaluation, high realized-data completeness, and separate
capital-limit/kill-switch review. RFC-007 itself cannot authorize live work.

## 29. Direct answers and decision

1. RFC-007 can safely read the active append-only observer.
2. It modified no observer source or output.
3. Records ingest incrementally without duplication.
4. Forced restart resumed without gaps.
5. Every replay-complete opportunity received a linked paper decision.
6. Incomplete opportunities remain partial or expire without fabrication.
7. Final outcomes linked deterministically at 100% in replay.
8. Paper results are explicitly not wallet-realized.
9. Model-ranked collection is not currently possible.
10. Burn-in uses the canonical least-crowded top-four equal-allocation baseline
    because it is deterministic, existing, and requires no model artifact.
11. Replay reached 100 consecutive eligible opportunities.
12. Replay Gate A passed.
13. Real-time Gate A has not started.
14. Opportunity-to-decision linkage was 100%.
15. Outcome linkage was 100%.
16. No duplicate decision was created.
17. No replay source record was missed or skipped by RFC-007.
18. No unresolved database-lock failure occurred.
19. Estimated size at 1,000 opportunities is about 9.3 MB.
20. The collector is ready to begin unattended real-time burn-in, with health
    monitoring and separate-terminal isolation.
21. The 1,000-opportunity research collection is not ready until real-time
    Gate A passes.
22. No live deployment is justified.
23. RFC-005 may be rerun only after the 1,000 paper-opportunity collection is
    complete for paper economics; a realized-economic rerun still requires the
    RFC-006 participant transaction, fee, wallet, reward, and claim thresholds.
24. Controlled-live consideration requires completed real-time Gate A, the
    frozen 1,000-opportunity paper study, a favorable preregistered economic
    result, directly validated protocol accounting, and an independently
    reviewed live-safety RFC. None is satisfied by replay alone.

Decision: replay burn-in passed; the collector is ready to begin a real-time
burn-in; model collection and RFC-005 rerun remain blocked; live testing
remains unjustified.

## 30. Recommended next phase and launcher

Open a new terminal. Do not stop or reuse the observer terminal.

```bash
cd /Users/anisbaker/Documents/orev3
source .venv/bin/activate
export PYTHONUNBUFFERED=1
PYTHONPATH=src python -m orev3.collection.cli run \
  --config config/collection/rfc007_burn_in_v1.json \
  --ledger data/ledger/rfc007_live_ledger_v1.sqlite \
  2>&1 | tee -a logs/rfc007_paper_collection_v1.log
```

No wallet, private key, or RPC mutation environment variable is required.

Safe shutdown: press Control+C in the RFC-007 terminal only. Do not stop the
observer terminal.

Restart with the identical command. The cursor and single-writer lease protect
resume.

Health:

```bash
PYTHONPATH=src .venv/bin/python -m orev3.collection.cli health \
  --ledger data/ledger/rfc007_live_ledger_v1.sqlite \
  --mode real_time_burn_in
```

Gate A:

```bash
PYTHONPATH=src .venv/bin/python -m orev3.collection.cli evaluate-burn-in \
  --ledger data/ledger/rfc007_live_ledger_v1.sqlite \
  --mode real_time_burn_in
```

After real-time Gate A passes, freeze the start marker and run the four-block
1,000-opportunity paper collection without strategy or boundary changes.
