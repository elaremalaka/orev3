# ORE Miner V3 — Project Snapshot 004

## Milestone

The ORE Miner V3 Observer and Snapshot Collector foundation has completed long-duration validation.

This milestone validates the project's ability to collect immutable, high-frequency ORE protocol observations reliably enough to begin building the Historical Dataset and Round Lifecycle Assembler.

---

## Overnight Validation

Snapshot Collector V2 completed an overnight sustained collection test.

Observed results:

- 33,956 valid snapshots
- 0 malformed JSON records
- Approximately 9.5 hours of observation
- 439 distinct observed ORE rounds
- Round range: 342132 through 342570
- Median snapshot interval: approximately 1.008 seconds
- Maximum observed snapshot gap: approximately 3.1 seconds
- 183 observed u64::MAX round-initialization states

The overnight dataset demonstrated stable long-duration operation using the current private RPC tier.

No RPC tier upgrade is currently required.

---

## RPC Slot Regressions

22 observations were identified where rpc_slot decreased relative to the immediately preceding observation.

These regressions were concentrated primarily in several localized periods.

Examples included regressions during:

- Round 342216
- Rounds 342249–342250
- Round 342341

Observed regressions ranged from small single-slot movements to larger temporary regressions.

Collector timestamps continued progressing normally.

### Treatment

Raw snapshots must not be modified, deleted, reordered, or rewritten to hide these observations.

The Observer records what the RPC reports at observation time.

The Historical Dataset layer will identify and annotate slot regressions using data-quality metadata such as:

rpc_slot_regression = true

Raw observations remain immutable.

Downstream analysis may decide whether specific regressed observations should be included or excluded for a particular use case.

---

## Round Account Transition Race

One snapshot collection failure was observed where:

- The Board referenced a newly advanced round ID
- The corresponding Round account was not yet available through the RPC

This is consistent with a temporary round-transition race.

### Treatment

This does not block the project.

Future collector improvements may classify this condition explicitly as:

round_account_pending

rather than as a generic snapshot error.

The Historical Dataset layer must recognize that short-lived transitional gaps can occur around round boundaries.

---

## Round Initialization State

During round transitions, the Board may temporarily report:

end_slot = u64::MAX

Collector V2 correctly preserves this raw value and reports the round as:

initializing

During this state:

slots_remaining = unknown

The overnight test captured 183 initialization-state snapshots.

These states must remain part of the historical record because they represent information actually available to a miner at that point in time.

---

## JSONL Integrity

Collector V2 produced:

- 33,956 valid overnight snapshots
- 0 malformed JSON records

The hardened append-only JSONL writer is therefore considered validated for sustained collection.

Historical malformed data from Snapshot Collector V1 remains preserved but must be handled gracefully by future readers.

---

## Session and Event Logging

Collector V2 provides:

- collector_session_id on schema-v2 snapshots
- session_start events
- session_stop events
- round_transition events
- snapshot_error events

This allows future systems to distinguish:

- Separate collector runs
- Intentional downtime
- Unexpected observation gaps
- RPC failures
- Round transitions

---

## RPC Usage

Collector V2 uses approximately three RPC requests per snapshot:

1. getSlot
2. getMultipleAccounts for Board and Treasury
3. getAccountInfo for the current Round

At the default one-second polling interval, expected sustained usage is approximately three requests per second.

The current private RPC allowance is 10 requests per second.

Long-duration validation demonstrated that this tier is sufficient for the current Observer.

No RPC tier upgrade is required at this stage.

---

## Observer / Collector Milestone Status

Protocol decoding: PASS

Board observation: PASS

Treasury / Motherlode observation: PASS

Active Round observation: PASS

Finalized Round inspection: PASS

Round transition capture: PASS

Initialization-state capture: PASS

Long-duration stability: PASS

RPC reliability: PASS

Snapshot cadence: PASS

JSONL integrity: PASS

Session tracking: PASS

Structured event logging: PASS

RPC slot regressions: PRESERVE AND FLAG

Round-account transition race: PRESERVE AND FLAG

The Observer and Snapshot Collector foundation is considered validated.

---

## Architecture Progress

Observer:

COMPLETE FOR CURRENT MILESTONE

Historical Dataset / Round Lifecycle Assembler:

NEXT

Replay Engine:

NOT STARTED

Strategy Lab:

NOT STARTED

Decision Engine:

NOT STARTED

Portfolio Simulator:

NOT STARTED

Paper Miner:

NOT STARTED

Live Miner:

NOT STARTED

Adaptive Strategy Layer:

NOT STARTED

---

## Historical Dataset Design Requirements

The next layer will transform immutable raw observations into structured historical round records.

It must not modify raw data.

The Round Lifecycle Assembler must support:

- Schema V1 and Schema V2 snapshots
- Multiple daily JSONL files
- Multiple collector sessions
- Malformed-record tolerance
- Round grouping by round_id
- Chronological observation ordering
- RPC slot regression detection
- Observation gap detection
- Round initialization states
- Round transitions
- Partial round coverage
- Finalized round state
- Data-quality annotations

The assembler must distinguish between:

1. Raw observations
2. Derived lifecycle records
3. Data-quality metadata
4. Finalized outcomes

Derived historical datasets must be reproducible from the immutable raw source data.

---

## Next Step

Design and implement the Historical Dataset / Round Lifecycle Assembler.

The first version should:

1. Read raw observer JSONL files.
2. Support schema V1 and V2.
3. Skip and report malformed records without modifying source files.
4. Group observations by round_id.
5. Sort observations chronologically.
6. Detect collector sessions.
7. Detect RPC slot regressions.
8. Detect significant observation gaps.
9. Identify initialization states.
10. Determine whether round coverage is complete or partial.
11. Preserve finalized-round information where available.
12. Produce reproducible derived round lifecycle records.

The continuous Observer may continue collecting raw data independently while downstream systems are developed.

