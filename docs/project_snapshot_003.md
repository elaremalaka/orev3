# ORE Miner V3 — Project Snapshot 003

## Milestone

Snapshot Logger V1 completed its first sustained real-world collection test.

The purpose of this test was to validate continuous raw-data collection across multiple ORE rounds before beginning the Historical Dataset layer.

The test successfully exposed several operational edge cases that need to be addressed before the collector is considered production-quality.

---

## Snapshot Logger V1 Test Results

The uploaded dataset contained approximately:

- 2,536 valid snapshots
- 55.8 minutes between the first and last valid snapshot
- 31 distinct round IDs
- Median snapshot interval of approximately 0.807 seconds

The collector successfully:

- Captured live Board state
- Captured live Treasury state
- Captured current Round state
- Captured multiple round transitions
- Preserved all 25-square arrays
- Tracked Motherlode progression
- Continued operating across transient RPC failures

---

## Issue 1 — RPC Rate Limiting and Timeouts

During sustained collection, the public Solana RPC produced:

- HTTP 429 rate-limit responses
- RPC timeouts
- Missing observation periods

Several significant collection gaps were observed.

The collector did recover automatically at the outer collection-loop level, but failed snapshot attempts were not preserved as structured data.

### Resolution

The collector was redesigned to include bounded RPC retry behavior.

Retries now cover:

- HTTP 429 responses
- HTTP 5xx transient server failures
- Network timeouts
- Network request failures

Retry behavior uses exponential backoff with jitter.

The collector now supports use of a private RPC through:

ORE_RPC_URL

The RPC URL remains local and must never be committed to the repository.

---

## Issue 2 — Excessive RPC Request Usage

Snapshot Logger V1 performed approximately four RPC calls per snapshot:

1. getSlot
2. getAccountInfo Board
3. getAccountInfo Treasury
4. getAccountInfo Round

At a 0.8-second polling interval, this increased the likelihood of rate limiting.

### Resolution

Board and Treasury account reads are now combined using:

getMultipleAccounts

The expected RPC usage per snapshot is now approximately:

1. getSlot
2. getMultipleAccounts for Board + Treasury
3. getAccountInfo for current Round

This reduces expected usage to approximately three RPC requests per snapshot.

The default polling interval was also changed:

0.8 seconds -> 1.0 second

Expected sustained RPC usage is therefore approximately three requests per second.

The current private RPC allowance is 10 requests per second.

The higher 50 requests-per-second RPC tier is not currently considered necessary.

The project should first demonstrate reliable operation within the current 10 requests-per-second allowance.

---

## Issue 3 — Temporary Round Initialization State

During round transitions, the Board account was observed with:

end_slot = 18446744073709551615

This value equals:

u64::MAX

The value appeared during temporary round-transition states.

Treating this as a normal end slot produces an invalid and extremely large slots_remaining value.

### Resolution

Collector V2 explicitly detects:

end_slot == u64::MAX

The collector classifies this state as:

round_status = initializing

During this state:

slots_remaining = unknown

The raw end_slot value remains preserved in the immutable snapshot.

This distinction is important for future replay and round lifecycle reconstruction.

---

## Issue 4 — Malformed JSONL Record

One malformed JSONL line was discovered in the first sustained dataset.

The cause has not been conclusively established.

The remainder of the dataset contained valid JSON records.

### Resolution

The JSONL writer was hardened.

Writes now use:

- O_APPEND
- One encoded JSON line per write operation
- A single os.write call

The goal is to reduce the possibility of partial or interleaved writes.

Raw files remain append-only.

Existing historical data will not be modified or deleted.

---

## Issue 5 — Collector Errors Were Terminal-Only

Snapshot Logger V1 printed collection failures to Terminal but did not preserve them.

This made it difficult to distinguish:

- Intentional collector downtime
- RPC outages
- Rate limiting
- Timeouts
- Other collection failures

### Resolution

Collector V2 introduces structured operational event logs.

Event files are stored locally as:

logs/collector_events_YYYY-MM-DD.jsonl

Events include:

- session_start
- session_stop
- snapshot_error
- round_transition

Errors include:

- UTC timestamp
- Collector session ID
- Error type
- Error message

Operational logs are separate from immutable raw protocol snapshots.

---

## Issue 6 — Collector Sessions Were Not Identifiable

Stopping and restarting Snapshot Logger V1 appended data to the same daily JSONL file.

Although timestamps preserved chronological ordering, there was no explicit identifier distinguishing separate collector runs.

### Resolution

Collector V2 generates a UUID for every collector process.

Each schema-v2 snapshot contains:

collector_session_id

Structured collector events also contain the same session ID.

This allows future analysis to distinguish:

- Continuous observation periods
- Intentional restarts
- Separate collector runs
- Gaps within a running session

---

## Schema Version Change

The Observer snapshot schema has been updated:

schema_version 1 -> schema_version 2

Schema V2 adds:

collector_session_id

Existing schema-v1 snapshots remain valid historical raw observations.

They will not be rewritten.

Future dataset tooling must support reading multiple historical schema versions.

---

## Data Preservation

Raw observer snapshots continue to be stored as:

data/raw/observer_YYYY-MM-DD.jsonl

Files rotate by UTC date.

Restarting the collector on the same UTC date:

- Does not overwrite the file
- Does not delete previous observations
- Appends new observations

A new UTC date automatically produces a new dated file.

Raw snapshot data and collector event logs remain local and must not be committed to Git.

---

## Security

The private RPC endpoint may contain credentials or an API token.

It must:

- Never be hardcoded
- Never be added to source files
- Never be added to documentation
- Never be committed to Git
- Never be pasted into public logs

The collector reads the endpoint from:

ORE_RPC_URL

The actual value remains local.

The existing repository security policy remains in force.

---

## Current Architecture Status

Observer:

Core protocol decoding validated.

Snapshot Logger V1:

Initial sustained test completed.

Snapshot Logger V2:

Implemented and awaiting validation.

Historical Dataset:

Not started.

Replay Engine:

Not started.

Strategy Lab:

Not started.

Decision Engine:

Not started.

Portfolio Simulator:

Not started.

Paper Miner:

Not started.

Live Miner:

Not started.

Adaptive Strategy Layer:

Not started.

---

## Next Validation Test

Before beginning the Historical Dataset layer, Snapshot Logger V2 will run for approximately 15–20 minutes.

The validation will check:

- RPC reliability
- Retry behavior
- Snapshot frequency
- Missing observation periods
- Duplicate slots
- Round transitions
- u64::MAX initialization states
- Structured error events
- Session tracking
- JSONL integrity
- Schema-v2 consistency

If this validation passes, the project can proceed to designing the Historical Dataset / Round Lifecycle Assembler.

