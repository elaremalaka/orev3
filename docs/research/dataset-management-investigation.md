# Dataset Management Pipeline Investigation

**Date:** 2026-07-30  
**Status:** Investigation complete  
**Scope:** Research Domain, read-only profiling and root cause analysis

## 1. Executive summary

The managed dataset did not require approximately three hours because JSON
parsing, lifecycle assembly, serialization, or validation is intrinsically
slow. A successful build is modeled at approximately **46.03 minutes** for
the measured collection. Outcome enrichment accounts for **45.52 minutes
(98.90%)** of that time. All measured local work accounts for approximately
30.45 seconds.

The approximately three-hour operator-visible duration was cumulative. It
included:

1. an initial build rejected by a malformed observer record;
2. a long sandboxed-network attempt that applied bounded RPC retries to each
   serial lookup despite the same network-resolution failure;
3. a complete enrichment pass whose later validation failed on provisional
   `start_slot` handling, causing the enrichment work to be discarded;
4. the final successful enrichment and build pass;
5. diagnosis and validation between attempts.

The published dataset contains 6,313 rounds:

- 610 outcomes observed directly in observer data;
- 1,073 outcomes recovered by RPC enrichment;
- 4,630 outcomes still missing.

Every one of the 4,630 missing outcomes was probed during this investigation
with the same address derivation, account decoding, and finality rules used by
the enricher. Every lookup returned an unavailable account. There were no
HTTP 429 responses, timeouts, network failures, decode failures, or
not-finalized accounts in the complete probe.

The strongest evidence is the temporal boundary. All enriched outcomes in the
published dataset are from rounds 349463 through 350603. All missing outcomes
end at round 349462. At investigation time, only 1,000 of the 1,073 previously
enriched accounts remained available. This is consistent with a moving
account-availability window. A null `getAccountInfo` response does not by
itself distinguish account closure, pruning, or another provider-side
availability policy, so the narrower finding is: the finalized account data
needed by the current enrichment algorithm was no longer available from the
configured RPC endpoint.

Replay readiness is limited principally by missing outcomes, not by lifecycle
assembly:

- dataset integrity is valid;
- 6,296 of 6,313 rounds have complete lifecycle coverage;
- only 17 rounds are incomplete;
- 4,630 rounds have no finalized outcome.

## 2. Method

No repository implementation was changed for this investigation.

Temporary instrumentation measured the existing functions and was removed
after use. It:

- discovered observer sources;
- measured a warm-cache raw file scan;
- measured `read_observer_files`;
- separated approximate raw I/O time from JSON/Pydantic normalization time;
- measured `assemble_rounds`;
- measured index-record construction;
- wrote a temporary dataset under `/tmp`;
- validated every observation reference;
- generated and hashed temporary metadata;
- removed the temporary files.

A separate read-only RPC probe examined every non-observed round in the
published managed dataset. The probe used:

- `derive_round_address`;
- `SolanaRpcClient.get_account_info`;
- `decode_round`;
- `is_finalized_round_state`;
- `SolanaRpcClient.get_slot` when an outcome was available;
- the builder's configured 0.25-second per-attempt pacing delay.

The local stage profile used the collection available at profiling time:
9 files, 497,120 parsed snapshots, and 6,386 lifecycles. The published outcome
analysis remains anchored to the managed artifact:
8 files, 491,401 snapshots, and 6,313 lifecycles. The observer remained active,
so later files and lines are not retroactively part of the published artifact.

The source file cache was warm during the raw-I/O measurement. The I/O number
therefore characterizes this run, not cold-storage performance. It does not
affect the conclusion because raw I/O is less than 0.01% of modeled runtime.

## 3. Runtime profile

The table combines the measured local stages with the complete paced RPC
probe. Percentages use the 2,761.70-second modeled successful-build runtime.
Index-record generation is shown separately because it occurs between
enrichment and writing.

| Stage | Wall time | Total | Items | Throughput |
|---|---:|---:|---:|---:|
| Observer discovery | 0.0003 s | <0.001% | 9 files | 34,510 files/s |
| Source file reading | 0.1485 s | 0.005% | 497,109 lines, 532.1 MB | 3.35M lines/s |
| Snapshot parsing and normalization | 12.2888 s | 0.445% | 497,120 snapshots | 40,453 snapshots/s |
| Lifecycle assembly | 1.4802 s | 0.054% | 497,120 snapshots, 6,386 rounds | 335,846 snapshots/s |
| Outcome enrichment | 2,731.2493 s | 98.898% | 5,703 attempted rounds | 2.09 rounds/s |
| Index-record generation | 2.7449 s | 0.099% | 6,386 rounds | 2,326 rounds/s |
| Dataset writing | 0.4702 s | 0.017% | 6,386 records, 80.4 MB | 13,580 records/s |
| Validation | 13.2714 s | 0.481% | 497,120 references | 37,458 snapshots/s |
| Metadata generation and hashing | 0.0444 s | 0.002% | 1 metadata record | 22.5 records/s |
| **Modeled total** | **2,761.6979 s (46.03 min)** | **100%** | | |

### 3.1 Enrichment decomposition

The complete probe made 5,703 account attempts. It took 2,731.25 seconds:

- configured sleeps: 1,425.75 seconds (52.20%);
- RPC request latency: 1,270.35 seconds (46.51%);
- address derivation, decoding, bookkeeping, and loop overhead:
  approximately 35.15 seconds (1.29%).

Mean measured RPC time per attempted round was 0.2228 seconds, median was
0.2642 seconds, and maximum was 0.7934 seconds. These figures include the
additional `getSlot` request for accounts that resolved to finalized outcomes.

The successful published build attempted 5,703 rounds lacking an observed
outcome. It issued one serial `getAccountInfo` request for each. For each of
the 1,073 successful enrichments it then issued a separate `getSlot` request.
The fixed delay was also applied after unavailable and failed attempts.

## 4. Why the operator-visible effort approached three hours

The approximately three-hour duration was an execution-history total, not one
successful pipeline profile.

| Attempt or activity | Result | Runtime effect |
|---|---|---|
| Initial source read | One malformed raw record caused the original builder to stop | Short failure, followed by diagnosis |
| Sandboxed RPC build | DNS/network access was unavailable; the RPC client performed bounded retries per serial round | Approximately 90 minutes before interruption |
| First network-enabled full pass | Enrichment completed, then validation found initialized/provisional start-boundary mismatches | Approximately one full enrichment pass was discarded |
| Corrected successful pass | Enrichment, write, validation, and metadata publication succeeded | Approximately one full enrichment pass |
| Focused and repository validation | Tests, compilation, statistics, and Git verification | Additional operator-visible time |

The pipeline has no checkpoint between enrichment and validation. A validation
failure therefore discards all enrichment results. A new invocation reparses
the sources and reissues all enrichment requests. This explains why two full
passes cost roughly twice the single-build profile.

The uniform network failure was especially expensive because `enrich_round`
catches each terminal exception and returns a per-round `failed` status.
`enrich_rounds` then advances to the next round. A provider-wide connectivity
failure therefore does not terminate the batch early; the same retry/backoff
policy is paid independently for every attempted round.

## 5. Outcome completeness

### 5.1 Published result

| Outcome source | Rounds | Share of 6,313 |
|---|---:|---:|
| Observed finalized outcome | 610 | 9.66% |
| RPC-enriched finalized outcome | 1,073 | 17.00% |
| Missing finalized outcome | 4,630 | 73.34% |
| **Total** | **6,313** | **100%** |

The observer supplied a finalized protocol state for only 610 rounds.
Lifecycle coverage marked "complete" means observations cover the round's
start and end boundaries within the documented polling margin. It does not
mean that an explicit finalized account state was observed before the
collector moved to the next active round.

The builder therefore attempted RPC enrichment for 5,703 rounds. It recovered
1,073 and could not recover 4,630.

### 5.2 Exclusive missing-outcome classification

The primary classification below accounts for every missing round exactly
once.

| Primary reason | Count | Evidence |
|---|---:|---|
| Finalized outcome absent from observer source and round account unavailable from RPC | 4,630 | Complete read-only probe of all 4,630 missing rounds |
| RPC timeout | 0 | Complete probe |
| HTTP 429 / exhausted rate limit | 0 | Complete probe |
| Network failure | 0 | Complete probe |
| Account present but not finalized | 0 | Complete probe |
| Account decode failure | 0 | Complete probe |
| Lifecycle assembly integrity failure | 0 | Published dataset validates structurally |
| **Total** | **4,630** | |

### 5.3 Orthogonal observer-coverage classification

Coverage is reported separately because incomplete coverage and RPC account
availability can coexist.

| Lifecycle coverage among missing outcomes | Count |
|---|---:|
| Complete lifecycle | 4,618 |
| Partial start | 6 |
| Partial end | 4 |
| Partial both | 2 |
| **Total** | **4,630** |

Thus, incomplete observer coverage is associated with 12 missing outcomes but
does not explain the other 4,618. The direct blocker for all 4,630 is that the
observer source lacks a finalized outcome and the later account lookup returns
no account.

### 5.4 Temporal availability evidence

- Missing outcomes: rounds 342063 through 349462.
- Enriched outcomes: rounds 349463 through 350603.
- At publication: 1,073 accounts were enrichable.
- At investigation: 1,000 of those accounts remained enrichable.
- Seventy-three formerly enrichable accounts had become unavailable.

This moving boundary is incompatible with a fixed lifecycle-assembly defect
and consistent with time-sensitive account availability. The exact external
cause cannot be proven from `getAccountInfo == null` alone.

## 6. Replay readiness

`ready_for_replay` requires:

1. structural integrity;
2. at least one replay round;
3. zero incomplete rounds;
4. zero missing outcomes.

Current state:

| Gate | Result |
|---|---|
| Structural integrity | PASS |
| Nonempty dataset | PASS — 6,313 rounds |
| No incomplete rounds | FAIL — 17 incomplete |
| No missing outcomes | FAIL — 4,630 missing |
| Metadata consistency | PASS |
| Overall readiness | **FAIL** |

Missing outcomes are the dominant blocker. Resolving all missing outcomes
would still leave 17 incomplete lifecycles. Conversely, repairing only the 17
coverage gaps would leave 4,630 missing outcomes.

The one malformed raw source line is recorded in metadata and excluded because
it cannot be normalized into an observer snapshot. It is not referenced by the
managed dataset and does not make the remaining managed artifact structurally
invalid.

## 7. Bottleneck and repeated-work analysis

### 7.1 Highest runtime contributors

1. Serial RPC enrichment: 98.90%.
2. Independent reference validation: 0.48%.
3. Snapshot parsing and normalization: 0.45%.
4. Index-record generation: 0.10%.

Dataset writing and metadata are not material bottlenecks.

### 7.2 Repeated RPC work

Each build starts from raw observer data and does not reuse outcomes from the
previous managed artifact. Consequently:

- every round without an observed outcome is looked up again;
- persistently unavailable old accounts are queried on every build;
- already enriched outcomes are fetched and decoded again;
- a separate `getSlot` request is made for each successful enrichment;
- a failed post-enrichment validation causes all network work to be repeated.

The RPC client already exposes `getMultipleAccounts`, but the enrichment loop
uses `getAccountInfo` serially.

### 7.3 Serialization and rescans

Current work is linear, but it is repeated:

- the source reader parses every observer snapshot;
- validation scans each source file once to build line offsets;
- validation then seeks, reads, parses, and normalizes every referenced source
  observation again;
- the generated dataset is read again to compute its SHA-256.

The second normalization pass is intentionally independent validation, but it
costs 13.27 seconds. This is negligible beside enrichment.

### 7.4 O(n²) behavior

No O(n²) behavior was measured in the current validator. It creates one
line-offset index per source file and performs one seek/read per reference,
making source-reference validation O(source lines + references).

The implementation that predated the managed build correction reopened and
rescanned a source file from line one for every reference. That design was
O(references × average source position) and was not viable at approximately
half a million snapshots. It was no longer present in the profiled pipeline.

### 7.5 Active-source boundary

The observer continued appending while profiling. Discovery increased from
8 files in the published build to 9 files during investigation. An individual
reader invocation is deterministic for the lines it actually consumes, but
the source collection is not frozen across separate invocations. This does
not explain the long runtime, but it affects reproducible statements about
"latest" data.

## 8. Recommendations

These are investigation recommendations only. No implementation is included.

| Priority | Recommendation | Effort | Expected runtime improvement | Expected completeness improvement | Architectural risk |
|---:|---|---|---|---|---|
| 1 | Durably capture or archive finalized outcomes while they are still observable, with explicit Research/Production promotion boundaries | High | Eliminates most later enrichment for newly captured rounds; successful rebuilds approach local-stage time | Potentially recovers most of the current 73.34-point outcome gap for future collections; historical unavailable accounts still require another authoritative source | High — touches observer/production boundaries and must preserve point-in-time and provenance rules |
| 2 | Batch unresolved account lookups with the existing multiple-account RPC capability and obtain contextual slot data per batch | Medium | Expected 10–50× reduction in enrichment wall time, subject to provider limits; approximately 45 minutes could become low single-digit minutes | No intrinsic recovery of unavailable accounts; may reduce transient rate-limit or request failures | Medium — response ordering, batch limits, partial failures, and evidence attribution must remain deterministic |
| 3 | Add a provenance-bound incremental enrichment cache and retry policy for unresolved rounds | Medium | Repeated builds over unchanged history could fall from approximately 45 minutes to seconds or low minutes | No direct gain from cached unavailable results; targeted scheduled retries may recover accounts before they disappear | Medium — stale negative results, finality, source identity, and cache invalidation must fail closed |
| 4 | Freeze an immutable source manifest/read boundary before a build | Low–Medium | Negligible speed improvement | None | Low — improves reproducibility while the observer remains active |
| 5 | Preserve independent validation while avoiding a second full Pydantic normalization when equivalent immutable evidence can be proven | Medium | Saves approximately 13 seconds (<0.5% of total) | None | Medium — risks weakening independent corruption detection |
| 6 | Persist enrichment status counts and sanitized failure categories in build metadata | Low | None | None directly; improves diagnosis and retry selection | Low |

## 9. Root cause conclusion

The pipeline's performance root cause is serial, non-incremental RPC
enrichment with fixed pacing and repeated work across build attempts.

The outcome-completeness root cause is that most observer lifecycles do not
contain explicit finalized state and the corresponding round account data is
no longer available by the time enrichment runs. It is not a replay,
Strategy Lab, lifecycle-assembly, JSON parsing, serialization, or validation
defect.

The replay dataset is structurally valid but not ready. Finalized-outcome
availability is the primary readiness limit; incomplete lifecycle coverage is
a much smaller independent limit.
