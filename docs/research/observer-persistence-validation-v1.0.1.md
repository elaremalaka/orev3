# Observer Persistence Validation — Version 1.0.1

## Status

Version 1.0.1 finalized-snapshot persistence is functioning correctly for the
currently running observer. Every explicit finalized state sampled in the
analyzed session was represented by exactly one local raw snapshot. The known
malformed historical JSONL record was logged and skipped; it did not prevent
the finalized append path from completing.

This result does not mean that every completed protocol round has a locally
observed outcome. The observer did not sample an explicit finalized state for
488 of the 510 rounds that had transitioned by the analysis cutoff. Those
gaps occur before persistence: the sampled records contain no finalized-state
indicator before the Board advances.

## Scope and cutoff

This was a read-only investigation. No observer process was stopped, started,
or signaled. No raw file, managed dataset, metadata file, source file, or
configuration was changed, and the replay dataset was not rebuilt.

Because the observer remained active, the measurements use the fixed cutoff
of `2026-08-01T16:42:50.800138+00:00`, the timestamp of the last session
snapshot included in the scan. Later records are intentionally outside this
report.

The repository was on branch `research/post-v1` at commit
`c0a430347eaa3d9ebda53edc7a5d21b2cf9ac4f1` during the investigation.

## Methodology

1. The live process command and start time were read from the operating-system
   process table. The session identifier and authoritative UTC start timestamp
   were read from `logs/collector_events_2026-08-01.jsonl`.
2. `data/raw/observer_2026-08-01.jsonl` was parsed with the repository's
   `orev3.historical.reader.read_observer_file()` implementation. Records were
   restricted to the active `collector_session_id`.
3. The restricted snapshots were assembled in memory with
   `orev3.historical.assembler.assemble_rounds()`. Nothing was written.
4. A local outcome was recognized only when the repository's explicit
   finalized-state indicators were present: a nonzero/non-uninitialized slot
   hash, entropy, positive `total_vaulted`, or positive `total_winnings`.
5. Session rounds were joined by `round_id` to the existing managed artifact,
   `data/derived/replay_dataset_v1.jsonl`. An outcome was classified as:

   - **observed** when the current session's raw records contained an explicit
     finalized snapshot;
   - **enriched** when no such local snapshot existed and the existing managed
     record declared `finalized_outcome_source = "enriched"`;
   - **missing** when neither source contained a finalized outcome at the
     cutoff.

6. Lifecycle completeness used the existing `quality.coverage_status` rule:
   only `complete` is counted as complete. Outcome completeness is
   `(observed + enriched) / replay rounds`.
7. The existing managed dataset was validated in place with the official
   dataset validator. Focused observer-persistence and dataset-management tests
   were run without modifying production artifacts.

## Current observer session

| Field | Value |
| --- | --- |
| Session identifier | `e24fb13b-8bf6-4d28-954c-4f169c15da32` |
| Observer PID | `29378` |
| Process command | `python -m orev3.observer.collect` |
| Session start, UTC | `2026-08-01T05:34:42.823547+00:00` |
| Process start, local | `2026-07-31 22:34:42 PDT` |
| First replay round | `352008` |
| First session snapshot | `2026-08-01T05:34:42.823842+00:00` |
| Last replay round at cutoff | `352518` |
| Last session snapshot at cutoff | `2026-08-01T16:42:50.800138+00:00` |
| Session snapshots analyzed | `39,603` |
| Structured `snapshot_error` events | `0` |

The session start is event line 269 in
`logs/collector_events_2026-08-01.jsonl`. The process table independently
matched the Python observer command and its start time.

## Quantitative results

### Current-session population

| Measure | Count | Share |
| --- | ---: | ---: |
| Replay rounds | 511 | 100.00% |
| Complete rounds | 487 | 95.30% |
| Incomplete rounds | 24 | 4.70% |
| Observed outcomes | 22 | 4.31% |
| Enriched outcomes | 388 | 75.93% |
| Missing outcomes | 101 | 19.77% |
| Outcomes available | 410 | 80.23% |

The exact outcome completeness is `80.234834%` (`410 / 511`). The missing
count includes round `352518`, which was still active at the cutoff.

Of the 510 rounds that had already transitioned, 22 had a local finalized
snapshot, 388 had an enriched outcome in the existing managed dataset, and
100 remained unavailable in that artifact. Thus 488 transitioned rounds
required enrichment because the current session did not locally observe their
finalized state; 388 had already been enriched and 100 were collected after
the managed dataset's cutoff and had not been incorporated.

### Existing managed dataset boundary

The managed dataset contains 405 rounds associated with this session,
`352008` through `352412`:

| Outcome source | Count |
| --- | ---: |
| Observed | 17 |
| Enriched | 388 |
| Missing | 0 |

The managed metadata was created at
`2026-08-01T14:23:18.178310+00:00`. Its final record is round `352412`, so it
cannot classify the session's subsequent 106 raw rounds. Five of those later
rounds already have local finalized snapshots; 100 transitioned rounds lack a
local final, and the final round at the analysis cutoff was still active.

The official validator reported 8,119 total managed replay rounds, 631,799
snapshots, 8,080 complete rounds, 39 incomplete rounds, 6,375 missing outcomes,
and `integrity_valid: true`. Its `ready_for_replay: false` result describes the
whole historical dataset's completeness, not corruption and not a failure of
the Version 1.0.1 persistence path.

## Finalized persistence evidence

The current session contains exactly 22 snapshots with explicit finalized
state, covering 22 distinct rounds. No finalized round has more than one such
snapshot. The round identifiers are:

`352009`, `352068`, `352117`, `352131`, `352139`, `352168`, `352185`,
`352217`, `352227`, `352277`, `352279`, `352282`, `352347`, `352373`,
`352378`, `352386`, `352390`, `352418`, `352420`, `352452`, `352463`, and
`352508`.

The first persisted example is raw line 19,666 for round `352009`, observed at
`2026-08-01T05:36:34.259008+00:00`. It contains all explicit final indicators:
a nonzero slot hash, entropy `7588131053051060436`, `total_vaulted = 703189949`,
and `total_winnings = 6328709543`. The managed dataset independently classifies
this round as `observed`.

The latest finalized example within the fixed cutoff is raw line 58,428 for
round `352508`, observed at `2026-08-01T16:30:31.353478+00:00`. It likewise
contains a nonzero slot hash, entropy `443054401281340954`,
`total_vaulted = 648224511`, and `total_winnings = 5834020601`.

The current observer log contains 22 occurrences of the warning for malformed
historical record
`data/raw/observer_v2_validatuion 2026-07-23.jsonl:6`. It contains zero
`snapshot_error` messages. The one-to-one count is significant: each time the
writer checked history for one of the 22 newly observed finalized rounds, it
encountered and skipped the malformed line, continued duplicate detection, and
the distinct finalized snapshot remained present in the append-only raw file.

This matches the implementation:

- `src/orev3/data/writer.py:23-45` defines the explicit finalization predicate.
- `src/orev3/data/writer.py:167-203` logs and skips malformed historical syntax
  while continuing the duplicate scan.
- `src/orev3/data/writer.py:213-232` still fails closed when a same-round record
  cannot be validated well enough to establish identity.
- `src/orev3/data/writer.py:266-289` appends a nonduplicate finalized snapshot
  with `durable=True`; `src/orev3/data/writer.py:48-113` performs the existing
  `fsync` behavior.
- `src/orev3/observer/collect.py:208-216` writes the collected snapshot before
  it evaluates the successor-round transition.
- `src/orev3/historical/assembler.py:20-74` requires an explicit local final
  indicator and labels that outcome `observed` at lines 383-430.

The live process began about 14 minutes after commit
`42b1756a76cb10eccb5fe08eb665349b13cc4df7` introduced the malformed-history
correction, and its observed behavior matches that correction.

## Missing-local-outcome evidence

There is no point after which finalized snapshots permanently cease to appear:
they are intermittent throughout the session, from round `352009` through
round `352508`. The absence pattern is therefore not a renewed
malformed-history abort.

The earliest round in the session without a local finalized snapshot is round
`352008`, beginning at `2026-08-01T05:34:42.823842+00:00`. The observer joined
that round late (`partial_start`) and recorded 33 snapshots. Every one has a
zero slot hash, null entropy, zero `total_vaulted`, and zero `total_winnings`.
The managed dataset later supplied an enriched outcome.

The earliest fully covered round without a local finalized snapshot is round
`352011`, beginning at `2026-08-01T05:37:53.516803+00:00`. Across all 79 raw
snapshots, none contains an explicit final indicator. Its last snapshot at
`2026-08-01T05:39:12.305644+00:00` is at RPC slot `436503184`, after board
`end_slot = 436503150`, but still contains a zero slot hash, null entropy, zero
`total_vaulted`, and zero `total_winnings`. The next poll observes the successor
round, and the managed record therefore classifies round `352011` as
`enriched`.

The earliest outcome still missing from both local raw data and the existing
managed artifact is round `352413`, first observed at
`2026-08-01T14:24:18.668194+00:00`. Its 79 local snapshots contain no explicit
final indicator, and the existing managed dataset ends at round `352412`.
Those two facts are the exact reason it remains missing at this report's
cutoff. The dataset was deliberately not rebuilt during this investigation.

## Conclusion

**Version 1.0.1 finalized persistence is functioning correctly according to
its defined trigger.** When `decode_round` supplied an explicit finalized
state, the current observer skipped the malformed historical record, completed
duplicate detection, and retained exactly one local finalized snapshot. No
duplicate finalized records or observer snapshot errors were found.

Local outcome completeness remains low because most completed rounds did not
present an explicit finalized state in any one-second sampled snapshot before
the Board advanced. That is an observation-coverage boundary upstream of the
writer, not a recurrence of the finalized-persistence bug. Existing enrichment
supplies 388 of those outcomes; post-dataset-cutoff rounds remain missing until
a future separately authorized dataset build.

## Read-only validation

- Managed dataset validation: `integrity_valid: true`; no rebuild performed.
- Focused tests: `24 passed` for
  `tests/observer/test_finalized_persistence.py` and
  `tests/dataset/test_management.py`.
- No behavioral, source, dataset, observer, or production changes were made.
