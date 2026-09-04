# RQ-003 Experiment 005 Bounded-Streaming Source-Processing Prerequisite v1

## Status

- Type: Prospective subordinate source-processing governance decision
- State: Adopted and frozen prospectively
- Experiment: `rq003-experiment-005-signed-share-imbalance-predictive-evaluation`
- Decision revision: `rq003-experiment-005-bounded-streaming-source-processing-prerequisite-v1`
- Scientific disposition: `SCIENTIFICALLY COMPATIBLE`
- Processing-model disposition: `BOUNDED STREAMING REQUIRED`
- Implementation authorized: No
- Source membership change authorized: No
- C2 inclusion authorized: No
- Protocol or scientific revision authorized: No
- Adapter adoption authorized: No
- Registry modification authorized: No
- Source S established: No
- Readiness execution authorized: No
- Outcome access authorized: No
- Provider authority authorized: No
- Wallet, transaction, capital, or SOL authority authorized: No

## 1. Purpose and controlling authority

This adopted clarification preserves the adopted bounded-streaming processing
model and prospectively freezes only its numeric-envelope measurement mode.
The preserved decision is subordinate to and does not alter:

- `docs/research/experiments/rq003-experiment-005-signed-share-imbalance-predictive-evaluation.md`, SHA-256
  `38afa9005bb43050d23e430335e11654c374d4e2d6f4a9f541782c005bffefdc`;
- `docs/research/governance/rq003-minimum-effect-scope-clarification-v1.md`, SHA-256
  `f736ac301a49be5acca58ef75f5130c1533328cf83cc359c9a69b596c53c2f4b`;
- `docs/research/governance/rq003-experiment-005-source-processing-prerequisite-v1.md`, SHA-256
  `d6d5d0fb3777cdb2a95e3bbff53b4815c574de68e31d4b5f7f1a0409580799a4`;
- `docs/research/governance/rq003-experiment-005-slice3-authority-prerequisite-v1.md`, SHA-256
  `d3e8748c63f0a870a3b1e1439fa73ada0145c7502bccc8fd834987e8fb29a36e`;
- `config/research/readiness/rq003-experiment-005-source-processing-v1.json`, SHA-256
  `042e2540554df3b7ba412bb0cd8821f8ae4b0f075b39679166107dd410ef4a63`; and
- `src/orev3/experiments/rq003_experiment5_source_processing.py`, SHA-256
  `16e67e96bc028f5bed29d7126b414ec51ceaafbc5f14923a266b221fe4c75a98`.

The current implementation cannot safely process the governed source. It
loads every complete member, retains split lines and parsed populations, and
constructs complete projection populations and payloads in memory. Raising
the existing limits without changing that model would create a multi-gigabyte
memory-exhaustion path. This is a processing-capacity correction only, not a
dataset selection or scientific revision.

## 2. Exact immutable source envelope

The controlling external-input identifier is
`rq003-experiment-005-replay-source-v1`. The member derivation, ordering, and
identity rules remain those frozen by the Slice-3 prerequisite. The following
table is the complete envelope. An implementation cannot add, omit, replace,
rename, reorder, or rebase a member.

| Order | Logical identifier | Member path | Bytes | SHA-256 | Member identity |
| ---: | --- | --- | ---: | --- | --- |
| 0 | `lifecycle` | `data/derived/replay_dataset_v1.jsonl` | 227867665 | `7680856bc6a01f9b69be0921d6e66b3f43d5241a38e63b37871b6925c1d59ba7` | `9dffdd3d206bfd2eb70f2909534f8eedafb1a3237e1e1cfaf0f31ff48beb0a48` |
| 1 | `observation.04247dceb9eef430807981b721cb06db848f94d2836cdcd3642b800d840e64f4` | `data/raw/observer_2026-08-01.jsonl` | 90747535 | `cafd93b594ad3260fbb4a32811328fa9b10b87d3c23bf56d4cd1f2817b063d9c` | `735d1a86d6acfffc26f6e30018ce6aab149c6f73bff46521c8ebc05c7b6efe8a` |
| 2 | `observation.052acfbe841c26f37e103481fd93e4c7ee5ecd031febd62a95e4824e94510c6f` | `data/raw/observer_2026-08-06.jsonl` | 90481458 | `bb495df19f583f9540a0d6b7b463c8629e35175c110ce50e461479770347a0bc` | `00a914f2e54267e936ba62863813e706d592bee6a90c04be4b51eb6b43b28c96` |
| 3 | `observation.3725e3c554bf69e5304b7fa41076ccccef9132efb70048c332eb171fe0326d56` | `data/raw/observer_2026-08-07.jsonl` | 90269649 | `97996586eed5bb18881f665c9743e036c09b7d38a0c8c3ddd3c9cb6365ec0292` | `61b5db3f11cc7ad3d6ada3d1bc24a6e889935cdaad5b140557fa0971a7ab1816` |
| 4 | `observation.3f09a2f4ba638e7c4f9a6e5895c0be6f9ba487c188f099da013c9bf9eba24c1a` | `data/raw/observer_2026-08-04.jsonl` | 91389925 | `51cbfac3d8f82701c757676232663d1d95bfdbe058c88d3ad039ad7302c701d5` | `52bfd90d3170b3f305b8d343e0a6cbee9270e248bc79e60591713f842830a80f` |
| 5 | `observation.56d2fb4238c0772341a63a1a16fcf4dd0007b3f0a38d7c7404ceffeb359ed5b3` | `data/raw/observer_2026-07-29.jsonl` | 81137070 | `ad1bd0c072cb05ef18c6ea4609c3a229f7c691c86d96f2682984b6e2e0b8df13` | `1bb5992e67c5299f17b68d0352a331fb3aa0e6151fd66b4ee52c0c5c50a4aa4e` |
| 6 | `observation.730b83828a42622f9e9e951c61a78ff95b1ee9dcaee7ea6eaac83f19dbf3c732` | `data/raw/observer_2026-07-24.jsonl` | 69384019 | `075f5876d4bd1b659a4dabc65e4b8eb546ebb3306ebe15981cecabbd4e48e699` | `51e8fdaf03f051906c054c597ed43defa547f5168d120979e4b23831aa6742b2` |
| 7 | `observation.85c251f8e8a54e9de76e1128555c97f052e9781ecbd1a2caed49a729172bcfde` | `data/raw/observer_2026-08-10.jsonl` | 58002128 | `16a6b71e222965f4765d474cf9880fc549418b1bea522deaffc98c22baf7a9a2` | `d96c5e33cc550d3a2535651bd7909405d97b2fa4d669339f1d1284efa2032cf9` |
| 8 | `observation.865f8f4e7b82a1d1e1bea7e991bcc363c91b01cd110e9dfc3ea450e90f9812da` | `data/raw/observer_2026-07-25.jsonl` | 92094352 | `964e7195353b115353e767d7fa99593225172b1dd7b2e4d59b9221c13953389d` | `46d98dfca0beae4d6a84a3cc93b062e9147e6b9ce35a80ffe11474ab66b1983b` |
| 9 | `observation.8ee20e6270ef7fc19c243d6b21b94d60cdfa05f927e57d50f792972c09868a2d` | `data/raw/observer_2026-07-30.jsonl` | 91651671 | `b7d2725832d163dd8c47a2b53ca0d72fd71d414217371efba5da45cdf83f0e49` | `e524328f91af3c45ca5fa1c45f66905e9eadbb37c283bf2a348a38d668831bc6` |
| 10 | `observation.a05bfbdc9f959d89df68094d9db1c3040bea63712ed5302f0edb399c35a2e110` | `data/raw/observer_2026-07-31.jsonl` | 91716502 | `08f7ed845d77bf3970dcd218fc18c16a4c7975969ab5cbc8109a59530a6c25d2` | `45252e5ddc84eb021ec1aff09e8d8fea229246fce9bb63872e8c26f872e9e257` |
| 11 | `observation.a242d48907ba29d870ed1dbc970ecbc6dcc968c9aeee2c00bffb94fe831ef603` | `data/raw/observer_2026-08-03.jsonl` | 91463839 | `a08e697c556c7b5249f75fe7a42274ce9224abecbc322661c1636393feea8295` | `904b1379fa99292842c9f8ce557b228f54b4d56d73d75d40b07bc752ef1aa3cb` |
| 12 | `observation.c0b2aa8305438996ac95c600c2e964a43727632b2bdc24649196055fb7e5f16a` | `data/raw/observer_2026-07-27.jsonl` | 63975407 | `76c2ba0d2ddc8104b18e447d7d95dc9d32c0ed1b93765800817ee66eae9ef770` | `6e6c5872c61f9ce85f5aeb4961c6b6b4be24c8a475b0bf04c1dadd2f87ab437c` |
| 13 | `observation.c24bdcbb816a462ac0fa2b4fd31b666630af1ff54fe74b566ccfa21a94f55bfe` | `data/raw/observer_2026-07-26.jsonl` | 92031690 | `61c9dd2fd568a4706fd891238d9affdc51f6e7d6daf2028269a0657ec650c6e3` | `59cbd4839470631f56dfd5ff9399f2b68d7b2c04f795094c670f37603ed2cf32` |
| 14 | `observation.df599dc95f98d15490ea643ea4503c6bd51f97f7990c34ea733258b5bbd40822` | `data/raw/observer_2026-08-02.jsonl` | 91373046 | `23a458e609f76026ce0001f240ebe02a6c5b831bfefd32ecfa790c19ab4edea9` | `3452b331915633e7e83023f9ef754a5cec00139b6a5a1c24f224d4808812079b` |
| 15 | `observation.f2739d17afb1a6a0de364c537874251499beb18ce163aa39a60cbb95929ad0ec` | `data/raw/observer_2026-08-09.jsonl` | 70162016 | `8725afdcce78e204b9777d69c899465e7c681f613f05c177453166de7e3ffc0d` | `123e23fec05ba503d2af2ed95d6679bf64e1f10903de596bb52e6813c67324c1` |
| 16 | `observation.f5206062bf0dd94051aa58bb10fa8c52e833e126db2a97739cc170b3b890a990` | `data/raw/observer_2026-08-05.jsonl` | 91061023 | `5f9d3e1cc335a856aece18b691218bfaf5ad3b38fc9b524fd0dcc6f0803efb47` | `00a3ff472d1dc3398e37b889aa1475519cd99893c8c4f8a0ba7cb3bf3ced09e1` |
| 17 | `observation.f59df9bad2176d121b154630f5f8b4e191066a0c4e262eec28f681ba74fb25d5` | `data/raw/observer_2026-07-23 - overnight.jsonl` | 36417273 | `844cc4fab01b448c621f0b0478707fe89866baaa0b0d4499e62ee1d282e49431` | `ff05561a7854b930fca409e1dd1f6adb36d7ac21f5b18bc45c6ab952ba50846d` |
| 18 | `observation.f73b78f21eaa8ce19daf680a76718f1b87a2a2aac9e4959793d0271531721c1a` | `data/raw/observer_2026-08-08.jsonl` | 89693849 | `95c8e6ae23c5e52c3dfbb3e8b1ea52028576a4c0e8b995d94ef9caf1df8b8943` | `0bd15795f876046567c3dfed7e025cea03003b118302d5aec6c6a25f59bc670b` |
| 19 | `observation.fd649dc7f4d157034fa2e11826110791e43cc219df1ba75ca9338b7350353add` | `data/raw/observer_v2_validatuion 2026-07-23.jsonl` | 3416507 | `d03229367181afe7d4da22a1ca095712ce860a1ac51bdad6874bce75eb576fdd` | `312f3458c948666dcfb9aea6fb033dff8b74dccaeb1c1d9dd27e37e015262c00` |
| 20 | `observation.ff2eca1f1104d7b7f6dcb7e7fb9563f65a5c7884dcfb666517f3ace9edc7abaf` | `data/raw/observer_2026-08-11.jsonl` | 45472787 | `0bbd3542e32df2cd814c20eda0e67a13ff206690e309146947b93d6dc713ca99` | `4727513fe3455e8114e4d7857c6951652697dfbe472eb7b1f72630e7bfc71b65` |

The aggregate byte count is exactly `1749809411`; the combined lifecycle and
observation JSONL record count is exactly `1442676`; the lifecycle contains
`18653` records and exactly `1390766` observation references. The manifest
revision is `external-input-ordered-file-manifest-v1` and its identity is
`0387a21b4921428c932851c29bd790c5f70a7a3687d48df99614c6717f6d3658`.
There are no missing or invalid coordinates, duplicate member paths or
identifiers, NFC/path violations, or C2 members. The 23 unreferenced files
dated August 12 through September 3 remain excluded.

This table is source-envelope authority only. It is not a production external-
input declaration and does not establish an external-input identity, adapter,
registry membership, or Source S.

## 3. Immutable bounded source snapshot publication

Operational source bytes are copied into the existing private content-
addressed immutable snapshot store. Publication must:

1. open the declared source through the existing filesystem capability;
2. capture and validate the source descriptor state;
3. copy bounded chunks while incrementally computing SHA-256 and byte count;
4. reject before reading beyond the member or aggregate ceiling;
5. require exact declared byte count and SHA-256;
6. re-check stable descriptor state after the copy;
7. flush and atomically publish only after complete agreement; and
8. remove or leave non-authoritative every incomplete temporary object.

No complete operational member may be materialized in memory solely to create
the snapshot. Publication does not create a new durable source, spool,
database, artifact category, or resume authority.

## 4. Complete authentication before semantic influence

Every immutable member must complete a first framing/index pass before any
record from that member can influence selection, measurements, scientific
state, projection, or Replay. The pass recomputes byte count and SHA-256 and
requires exact agreement with the immutable snapshot authority. Before that
agreement, arbitrary operational bytes may be handled only in fixed-size
streaming I/O, hashing, LF framing, line counting, and offset construction;
no input-controlled bulk allocation or semantic influence is permitted.

Every byte and framed line participates in member byte count, SHA-256, stable
snapshot authentication, line numbering, offsets, and record count. The exact
frozen files require terminal LF and contain no CR framing or blank line; a
changed framing byte changes the authenticated digest and rejects. Lifecycle
lines are then parsed under the lifecycle authority. Only observation
coordinates named by authenticated lifecycle references are semantically
parsed under the observation whitelist/schema. Unreferenced observation lines
are never semantically parsed, diagnosed, indexed beyond offset/framing facts,
selected, measured, or projected.

The first pass may retain only offsets, framing facts, counts, and incremental
digests. It may not retain raw excerpts or semantic values. After complete
authentication, referenced-line parsing may observe only material authorized
by the existing whitelist. Parse-then-discard outcome handling remains
prohibited. Selection or scientific extraction before complete member
authentication is a hard failure. The malformed JSON at
`data/raw/observer_v2_validatuion 2026-07-23.jsonl` line 6 is unreferenced and
therefore scientifically inert; if that coordinate were referenced, strict
parsing would reject the graph exactly as frozen authority requires.

## 5. Compact coordinate and reference authority

The retained index must be finite and contain only information necessary for
deterministic access and conflict detection:

- for each member: ordered line-start offsets and the terminal byte offset;
- for referenced observation lines: membership bits or an equivalently compact
  monotone representation;
- for lifecycle records: line offsets, round ownership, chronology coordinates,
  and the compact ordered reference coordinates;
- the exact `(logical_identifier, source_file, source_line_number)` coordinate
  key needed for duplicate detection; and
- incremental member, record, and identity counters/digests.

Offsets are nonnegative integers bounded by the authenticated member byte
count. Every offset is checked against record framing when used. The index is
derived only from authenticated immutable snapshots and is invalidated on any
second-pass disagreement. It contains no raw JSON, raw excerpt, parsed
observation object, outcome value, provider locator, or executable callback.

The normal path must not retain 1,390,766 Python dictionaries or tuples when
compact offsets and coordinate representations suffice. The implementation
may choose a compact array encoding appropriate to the language runtime, but
that encoding must be deterministic, bounds-checked, independently
reconstructable, and demonstrated by memory evidence. It cannot alter the
logical coordinate or ordering authority.

## 6. Per-round authenticated reconstruction

After every source member is completely authenticated, processing revisits
lifecycle records in frozen `(start_slot, round_id)` chronology. It reads only
the observation lines referenced by the active lifecycle record from the
immutable snapshots. At most the active lifecycle round's semantically parsed
references, one current parsed observation, compact global index/identity
state, and fixed controller overhead may be retained.

The implementation must preserve all referenced future observations as
provenance, while selection remains the latest eligible observation at or
before `end_slot - 5`. Equal-RPC ordering remains exactly
`(observed_at_utc, source_file, source_line_number)`. Repeated but distinct
observations remain distinct. Missing, duplicate, conflicting, cross-round,
or differently authenticated coordinates reject exactly as under frozen
authority.

## 7. Incremental projection publication

Projection remains the existing closed canonical newline-terminated JSONL
representation and existing projection schema. For each lifecycle round the
processor constructs one record, validates it, canonicalizes it, and checks
whether appending its exact bytes would exceed `maximum_projection_bytes`.
An over-limit record is never committed to the candidate output.

The worker appends to an exclusive private output while incrementally
maintaining:

- projection SHA-256 and cumulative byte count;
- projection record count;
- the ordered lifecycle-record hash vector;
- the ordered projection-record identity vector; and
- the existing dataset-content, logical-projection-content, and projection
  identity materials.

It must not retain the complete projection record population or projection
payload in memory. A partial private output has no trusted identity and is
never published as authority.

## 8. Double reconstruction and Replay

The existing independent double-reconstruction requirement remains. The two
runs are sequential and each uses the same authenticated immutable snapshots
and frozen authority. They compare incrementally reconstructed complete byte
count, SHA-256, ordered record identities, lifecycle hash vector, dataset-
content identity, logical projection-content identity, and projection
identity. Exact canonical output bytes are compared by a bounded streaming
byte comparison of the two private immutable candidates. Two full payloads
must not be simultaneously resident in memory. Neither result becomes trusted
if any comparison differs.

Replay preparation must consume the authenticated projection as a bounded
JSONL stream. It may retain only Replay's bounded population/accounting state,
the current projection record, and the exact scientific state needed by the
current unit. It must not call an interface that returns the complete parsed
projection or complete projection bytes. Replay ordering, selection,
exclusions, identities, and scientific semantics remain identical.

## 9. Storage authority and failure atomicity

Only these existing authorities may hold bytes:

- immutable private source snapshot store;
- controller-private temporary roots;
- worker-private output roots; and
- content-addressed projection store.

No SQLite or other database, normalized-source spool, concatenated raw file,
durable resume journal, or new persistent artifact category is permitted.
Raw or outcome-bearing bytes may exist only in the already-authorized source
snapshots. Intermediate projection bytes may exist only in existing private
output/storage authority.

Temporary-disk enforcement uses a filesystem-reconstructable operation root
and a controller-owned logical-byte ledger. The private snapshot-store root
contains exactly `.orev3-bounded-streaming-v1/coordination.lock` and
`.orev3-bounded-streaming-v1/operations/`. The lock is an ordinary mode-0600
regular file opened without following links and locked with exclusive
`fcntl.flock(LOCK_EX)`. It is coordination metadata, not a durable semantic
journal or artifact. The lock is held during startup reconciliation, every
reservation transition, deduplicating publication, and cleanup; kernel close
or process death releases it.

An operation identifier is generated only by the controller as
`"op-" + secrets.token_hex(16)`: exactly 16 bytes from Python's OS-backed
CSPRNG, lowercase hexadecimal encoding, 32 hex characters, and prefix `op-`.
This is the same finite CSPRNG primitive already used for exclusive temporary
names in `src/orev3/execution/filesystem_capability.py`.
It is coordination authority, not scientific or artifact identity. Caller-
supplied, deterministic, timestamp-, PID-, or counter-derived identifiers and
substituted random generators reject. CSPRNG failure is the closed controller
failure `DISK_OPERATION_IDENTIFIER_GENERATION_FAILED`. Its mode-0700 root is
`operations/<operation_identifier>/` and contains a mode-0600 `lease` file,
plus the operation's controller, worker, snapshot-publication, and
reconstruction private subdirectories. Creation uses `mkdir` with `O_EXCL`-
equivalent no-replacement semantics; each collision consumes one attempt and
calls `secrets.token_hex(16)` again. Exactly 128 collisions reject without a
129th call as `RESOURCE_LIMIT_EXCEEDED`. The
controller holds an exclusive nonblocking flock on `lease` for the entire
operation. A second controller may run concurrently under another operation
root; paths and charges never merge.

The controller is the sole ledger authority. Before each worker launch it
creates one `AF_UNIX`, `SOCK_STREAM` socket pair, retains the controller end,
passes only the worker end as fixed descriptor 4 through the closed inherited-
descriptor mechanism in Section 10.1, and never places a descriptor number in
governed request material. No listener path exists and no other process receives
the endpoint. Section 9.1 is the sole wire authority. In particular, the
request is exactly its path-free seven-field object, the acknowledgment is
exactly its seven-field object, and the rejection is exactly its five-field
object. No path, alias, `reserved` shorthand, authorized-new-size response, or
other request/response representation is accepted.

`max_temporary_disk_bytes` charges full logical length of every operation-created
snapshot temporary, private controller file, worker output, and reconstruction
candidate. A reservation occurs before each bounded write and before publication;
one byte over rejects before growth. Pre-existing authenticated immutable
snapshot or projection objects charge zero. New objects remain charged until
verified deletion or successful atomic publication/handoff. Reconstruction one
remains charged while reconstruction two is written and compared. Hard links do
not reduce the creator's charge. Under the coordination lock, publication uses
the existing temporary-plus-`link` content-addressed mechanism: if another
operation won the name, the loser authenticates the target before deleting its
temporary and releasing that charge. Concurrent users of a previously published
object charge zero.

At startup, a controller takes the coordination lock and enumerates operation
roots by the exact name grammar without following links. It tries a nonblocking
exclusive flock on each `lease`: failure means a live operation and its root is
untouched; success means orphaned. Orphan charge is reconstructed as the sum of
`lstat` logical sizes of unique regular files beneath the confined root; any
link, special file, duplicate inode, invalid mode, or escaping path rejects
recovery closed. The orphan root is recursively deleted descriptor-relatively,
fsynced, and rechecked before a new operation is admitted. A crash during cleanup
leaves the root for the next identical pass. A crash during publication leaves
either a private temporary or an atomically linked content-addressed object;
the former is removed as orphan state and the latter remains untrusted until a
later operation independently authenticates and references it. No persistent
ledger or resume journal is introduced.

### 9.1 Reservation wire protocol

Each socket message is one 4-byte unsigned big-endian payload length followed
by exactly that many payload bytes. The length excludes the prefix, zero is
invalid, newline framing is absent, and native structs, pickle, and MessagePack
are prohibited. `MAX_RESERVATION_FRAME_BYTES` is exactly `294`. A length above
294 rejects before payload allocation. The receiver reads exactly four prefix
bytes and then exactly the declared payload; EOF during either is
`DISK_RESERVATION_PROTOCOL_REJECTED`.

Payloads use the existing readiness canonical JSON: strict UTF-8, sorted keys,
compact separators, finite integers only, no floats, no extensions, and
duplicate-key rejection. The received payload must parse and re-encode to
byte-identical canonical bytes. All protocol integers are JSON integers,
booleans excluded, in unsigned-64 range `0..18446744073709551615`; requested
growth is restricted to `1..18446744073709551615`.

The closed request contains exactly:

```text
schema_version: 1
message_type: "reserve_growth"
operation_id: "op-" plus 32 lowercase hex characters
sequence_number: unsigned-64
reservation_kind: one of "snapshot_growth",
  "controller_temporary_growth", "worker_output_growth",
  "projection_publication", "reconstruction_growth"
current_logical_bytes: unsigned-64
requested_growth_bytes: positive unsigned-64
```

Categories select controller-owned confined paths; the wire carries no path.
The controller requires `current_logical_bytes` to equal descriptor-derived
state for that category. The closed acknowledgment contains exactly:

```text
schema_version: 1
message_type: "reservation_acknowledged"
operation_id: the request operation_id
sequence_number: the request sequence_number
accepted_growth_bytes: exactly requested_growth_bytes
resulting_reserved_bytes: unsigned-64 checked ledger total
resulting_charged_bytes: unsigned-64 checked current charge
```

The closed rejection contains exactly `schema_version: 1`, `message_type:
"reservation_rejected"`, matching `operation_id`, matching `sequence_number`,
and `failure_code`, whose only values are `RESOURCE_LIMIT_EXCEEDED`,
`DISK_RESERVATION_PROTOCOL_REJECTED`, and
`DISK_RESERVATION_STATE_MISMATCH`. It contains no message, path, exception,
excerpt, or raw byte.

The expected sequence starts at unsigned integer zero. One valid request at the
expected sequence may receive one acknowledgment; only that acknowledgment
commits the reservation and advances expected sequence by exactly one. A
protocol, state, or resource rejection changes no ledger state and terminates
the reservation session immediately; its sequence is not advanced and no later
request is valid. Sequence `18446744073709551615` may be acknowledged once but
cannot advance or be followed by another request. Duplicate, stale, skipped,
replayed, or out-of-order request or response changes no ledger state. An
acknowledgment is single-use and grants only its matching category and growth;
it cannot authorize a later write.

One socket pair lasts for the worker lifetime. The controller creates it and
passes only the worker endpoint at descriptor 4 and shared lease descriptor at
descriptor 5 through the closed inherited-descriptor mechanism in Section
10.1; each process closes the unused socket endpoint immediately. The worker keeps
the lease descriptor open but cannot modify locking state, so controller death
cannot make a still-live worker appear orphaned. No reconnection, listener,
alternate IPC, or fallback exists. Orderly worker EOF is valid only with no
partial frame and no outstanding request. EOF with an outstanding request,
malformed frame, a second frame after terminal rejection, or trailing payload
bytes rejects. Controller EOF makes the worker stop before another write and
exit; worker death makes the controller retain outstanding charge and terminate
the operation. If acknowledgment has been issued and EOF or worker death occurs
before `fstat`/write reconciliation, the controller retains the greater of the
actual file size and acknowledged prospective size until the operation fails
and its root is removed.

The exact maximum is mechanically derived with maximum-width operation ID and
unsigned integers: the longest request (`controller_temporary_growth`) is 284
canonical bytes, the acknowledgment is 294, and the longest rejection
(`DISK_RESERVATION_PROTOCOL_REJECTED`) is 202. Therefore 294 is the maximum;
295 rejects before allocation.

The worker follows reserve, matching acknowledgment, then at most acknowledged
growth through the governed budgeted writer. It never writes before an
acknowledgment or beyond unused allowance. A short or failed write leaves the
unwritten allowance reserved until the next same-category request or orderly
EOF, when the controller verifies `fstat` and releases only the confirmed
unwritten difference. Worker death after acknowledgment charges the greater of
actual file size and the acknowledged prospective size until the operation is
failed and its root is removed. If the controller dies, the inherited lease
keeps the operation live until the worker observes socket EOF and exits; only
then may startup recovery classify and remove the orphan root.

Processing is all-or-nothing. Truncation, mutation during snapshot, digest or
count mismatch, second-pass mismatch, late malformed JSON, duplicate key,
invalid framing, missing/duplicate/conflicting reference, any byte/record/
projection/memory/disk/time exhaustion, deterministic reconstruction
mismatch, crash, or late projection failure produces no trusted partial
authority. Retry starts from the authenticated declared inputs; semantic
resume is prohibited. Closed canonical failure codes reveal no prohibited
field name, value, excerpt, exception frame, or source content.

## 10. Retained-state and complexity boundary

The normal Experiment 005 path must not retain:

- all complete source member byte strings simultaneously;
- all split source lines;
- all parsed observation records;
- all normalized reference dictionaries;
- all projection record dictionaries;
- complete projection bytes;
- two complete projection payloads for equality; or
- a complete parsed Replay projection.

Primary memory authority is structural allocation boundedness, not an
instantaneous operating-system quota. No hard kernel memory quota forms part
of this decision. Normal retained state is limited to fixed-size I/O buffers;
fixed-width per-member metadata; compact line-offset, reference/ownership,
duplicate/seen-coordinate, and lifecycle-round indexes; ordered lifecycle and
projection digest vectors; one active lifecycle record; at most one active
round's reference coordinates; one referenced observation record at a time;
one projection record; and fixed controller/runtime overhead. A per-round
representation is permitted only when its maximum cardinality is the frozen
146-reference bound and every element has a fixed, reviewed representation.

All count-to-byte multiplication, addition, offset advance, array sizing, and
allocation derived from input counts, record sizes, or cardinalities uses
checked nonnegative integer arithmetic before allocation. Overflow or a value
above its governing dimension rejects as `RESOURCE_MEMORY_EXCEEDED` before an
oversized semantic object is constructed.

The mechanically authenticated dimensions of the exact envelope are:

| Dimension | Exact ceiling and convention |
| --- | --- |
| total framed records | `1442676`, lifecycle plus every observation line |
| framed record bytes | `22694`, including the required terminal LF |
| decoded string-value bytes | `64`, UTF-8 bytes after JSON string decoding; keys excluded |
| decoded object-key bytes | `37`, UTF-8 bytes after JSON string decoding |
| canonical non-string scalar token bytes | `20`, UTF-8 bytes of strict canonical JSON for null, boolean, integer, or finite float; strings and keys excluded |
| JSON depth | `4`, root container or scalar counted as depth 1 and every nested array/object value adding 1 |
| object-member cardinality | `18`, members in any one decoded object |
| array cardinality | `146`, items in any one decoded array |
| lifecycle references per round | `146`, entries in one lifecycle `observation_references` array |

The record-byte ceiling bounds all raw lexical tokens, so no separate
input-token allocation may exceed 22,693 payload bytes before LF. Strict UTF-8
decoding, duplicate-key rejection, finite-number parsing, decoded key/value
limits, nesting, and container cardinalities are checked incrementally before
building the corresponding semantic value. Exact-bound inputs pass; one-over
values reject before allocation. Peak RSS is measured acceptance evidence
under Section 12, not proof replacing these structural constraints.

## 11. Resource-limit semantics and equality

The limits retain these exact meanings:

| Limit | Governed meaning |
| --- | --- |
| `maximum_members` | Maximum number of declared and snapshotted members. |
| `maximum_aggregate_bytes` | Maximum total operational input bytes admitted and authenticated into immutable snapshots. |
| `maximum_member_bytes` | Maximum admitted bytes of any one member. |
| `maximum_records` | Maximum combined lifecycle and observation JSONL records structurally scanned. |
| `maximum_projection_bytes` | Hard cumulative projection bound checked before an append would exceed it. |
| `max_temporary_disk_bytes` | Hard logical-byte ceiling on the operation ledger in Section 9. |
| `max_controller_peak_rss_bytes` | Post-run acceptance ceiling for the detached controller's measured maximum resident set size. |
| `max_worker_peak_rss_bytes` | Post-run acceptance ceiling applied separately to each measured child worker. |
| `watchdog_rss_bytes` | Defense-in-depth sustained-RSS termination threshold, not an instantaneous quota. |
| `watchdog_poll_interval_milliseconds` | Exact finite watchdog sampling interval adopted with the numeric envelope. |

The prospective source-envelope values are exactly:

- `maximum_members = 256`;
- `maximum_member_bytes = 227867665`;
- `maximum_aggregate_bytes = 1749809411`; and
- `maximum_records = 1442676`.

These exact values are permitted because every admitted member is also bound
by exact path, byte count, SHA-256, member identity, order, and manifest
identity. A larger source value requires separate justification and adoption;
no percentage, multiple, power-of-two, filesystem maximum, or ambient default
supplies authority.

The bounded-streaming generic policy in Section 11.1 must require the closed
fields `max_source_records`, `max_controller_peak_rss_bytes`,
`max_worker_peak_rss_bytes`, `watchdog_rss_bytes`, and
`watchdog_poll_interval_milliseconds`; none may be supplied through an ambient
default. Experiment-specific and generic values must be exactly
equal for member count (`maximum_members`/`max_collection_members`), aggregate
bytes (`maximum_aggregate_bytes`/`max_aggregate_collection_bytes`), member
bytes (`maximum_member_bytes`/`max_file_bytes`), source records
(`maximum_records`/`max_source_records`), and projection bytes
(`maximum_projection_bytes`/`max_projection_bytes`). Equality is authenticated
before processing; any inequality rejects and no minimum, fallback, or
override value is used.

`max_replay_units` is not a synonym for `maximum_records`: the former bounds
projected lifecycle source units consumed by Replay, while the latter bounds
all lifecycle plus observation JSONL records scanned. The current Replay-unit
limit may remain unchanged if it admits the exact projected lifecycle
population. Temporary-disk, memory, and timeout limits are generic worker/
controller policy and have no duplicate Experiment-configuration field; each
must nevertheless be carried explicitly into and enforced by every applicable
worker request. Snapshot admission, projection, Replay, and independent
reconstruction all bind the same adopted policy identity.

The sole measurement-only exception to final numeric representation is the
closed mode `BOUNDED_STREAMING_MEASUREMENT_CANDIDATE` defined in Section 12.
It does not weaken source limits or five-limit equality: the four frozen source
values remain integers and exact, and projection uses the identical finite
measurement-run integer in both Experiment and generic policy material. Only
the four RSS/watchdog fields use the exact non-null pending object while this
mode is selected. No other mode, marker, omission, or mixed representation is
valid.

Darwin 24.0.0 arm64 with CPython 3.14.5 supplies no usable instantaneous hard
memory quota for this authority: finite `RLIMIT_AS` installation fails,
`RLIMIT_MEMLOCK` does not limit ordinary allocation, Seatbelt is capability
confinement, and sampling cannot prevent an instantaneous peak. No rlimit,
container, VM, cgroup, or process-tree aggregate quota is claimed.

The primary authority is the structural allocation contract in Section 10.
The controller launches at most one child worker invocation at a time and
worker Seatbelt authority prohibits descendants. The arithmetic sum of
separately measured controller and worker RSS is conservative derived evidence,
not an independently enforced process-tree ceiling.

The governed-host production-shaped worker topology was directly observed as:

```text
supervising controller
  -> measurement_wrapper: /usr/bin/time -l
       -> governed_worker process instance:
            /usr/bin/sandbox-exec transition
            -> exec to authenticated Python worker
```

The PID returned by `os.posix_spawn` is persistent `/usr/bin/time`, which forks one child
in the same new process group and waits. `sandbox-exec` does not remain as a
concurrent process; it exec-replaces that child with Python without changing
PID or start time. The active group therefore contains two roles:

- `measurement_wrapper`: exact `/usr/bin/time` executable authenticated by the
  separate bounded measurement-wrapper authority below, direct spawned process,
  group leader, retained unreaped, monitored
  for identity but not used as worker RSS, and a termination target; and
- `governed_worker`: the time child, initially the exact authenticated
  `/usr/bin/sandbox-exec -p <authenticated-profile>` transition and then the
  same process instance exec'd to the exact authenticated Python executable and
  worker path; it is the watchdog RSS and worker acceptance target.

The existing `runtime-contract-v1.json` does not contain `/usr/bin/time` and is
not amended or reinterpreted. This decision selects a separate closed host-
runtime authority, `darwin-time-measurement-wrapper-v1`, revision `"1"`, at
exact absolute path `/usr/bin/time`. Its executable is a nonsymlink regular
mode-100755 file owned by uid/gid 0/0, byte count `135248`, and SHA-256
`22cd4718fa94a354326fa565cac137cb535bdc81d218d092b850733df7a1fa10`.
It has no useful version flag; executable bytes and host binding are the version
evidence. Identity domain is exactly
`orev3:bounded-streaming-measurement-wrapper:v1\n`; canonical identity material
is exactly `identifier`, `revision`, `executable_path`, `executable_mode`,
`executable_uid`, `executable_gid`, `executable_byte_count`,
`executable_sha256`, `architecture`, `darwin_release`, and
`host_system_identity`. With `architecture=arm64`, `darwin_release=24.0.0`, and
the frozen runtime host-system identity
`b3172c2aaaed62d9a559aea7d8ffaaf1ad4ed84dbd786030234c79ea85d3eeaa`,
the measurement-wrapper identity is
`09cc63835b888387783d32d0011fd0a0d344c3ba9620a947dfabd5bcfd521201`.
`reconstruct_bounded_streaming_measurement_wrapper_authority` in `runtime.py`
uses `lstat`, no-follow open, `fstat`, and bounded streaming SHA-256 before
every launch and during independent readiness/Git reconstruction. Wrong path,
link, type, mode, owner, size, bytes, host/runtime binding, or identity rejects;
claimed-identity resealing cannot replace the literals above.

### 10.1 Governed start gate and launch authority

The start gate is one anonymous POSIX pipe created by `runtime.py` with exactly
`os.pipe()`. Governed-host CPython 3.14.5 provides `os.pipe()` and creates both
endpoints non-inheritable; the alternate pipe-with-flags API is absent. Immediately after
creation, the controller requires `os.get_inheritable(fd) is False` for both
endpoints and requires `fcntl.fcntl(fd, fcntl.F_GETFD) & fcntl.FD_CLOEXEC` for
both. Any creation, query, or flag mismatch rejects. The write endpoint remains
controller-only and non-inheritable.

Launch uses exactly `os.posix_spawn`, absolute executable paths, and its Darwin
atomic file actions; no legacy subprocess pass-through launcher, parent-side `dup2`,
parent destination-FD mutation, save/restore sequence, `preexec_fn`, or launch
lock is used. Governed-host evidence demonstrated `os.posix_spawn`,
`POSIX_SPAWN_DUP2`, and `POSIX_SPAWN_CLOSE` through the actual
`/usr/bin/time -> sandbox-exec -> Python` chain and showed the mapped gate at FD
3 in Python. A second governed-host probe with `setsid=True` observed both the
session ID and process-group ID equal to the returned time-wrapper PID while
the Python child consumed the gate. The spawn uses exactly `setsid=True`,
establishing the persistent time wrapper as session and process-group leader;
its child remains in that group.

Descriptor numbers are fixed controller policy: 3 is the read-only start gate,
4 is the connected reservation-socket worker endpoint, 5 is the operation
lease, and 6 is the read-only request artifact. Before constructing file
actions, the controller verifies the four source descriptors are open,
non-inheritable, carry `FD_CLOEXEC`, have the exact distinct types/access modes,
and are four distinct open-file descriptions. A duplicate source or alias
rejects. Each source is then unconditionally duplicated, in target order 3, 4,
5, 6, with `fcntl.F_DUPFD_CLOEXEC` and minimum descriptor 7. Every scratch must
be greater than 6, unique, non-inheritable, and `FD_CLOEXEC`; otherwise all
scratch descriptors are closed and launch rejects.

The child file-action vector is fixed and ordered: open `/dev/null` read-only
onto FD 0; duplicate controller-created output-pipe scratch descriptors onto
FDs 1 and 2; duplicate the four normalized scratch descriptors onto FDs 3, 4,
5, and 6; then close every scratch descriptor. It does not explicitly close a
source descriptor whose number could have been overwritten as a destination;
all original sources are CLOEXEC and therefore disappear in the program exec.
All originals and scratches are CLOEXEC in the parent, and
`POSIX_SPAWN_DUP2` deliberately creates only the destination copies that survive
exec. Because every source first becomes a distinct scratch above 6, a source
already equal to its target, a source overlapping another target, 3/4 or 4/5
cycles, the full 3/4/5/6 cycle, unrelated parent occupants of 3 through 6, and
stdout/stderr allocation collisions all use the same non-cyclic action vector.
The parent never changes FDs 0 through 6, so pre-existing open or closed parent
destinations require no restoration and remain byte-for-open-file-description
unchanged on success or failure. An unconditional `finally` closes only this
invocation's source copies, output-pipe child endpoints, and scratches after
`os.posix_spawn` returns or fails; the controller endpoints it still owns remain
according to their protocol lifetimes.

`os.posix_spawn` consumes the immutable file-action vector synchronously before
return. No parent-global descriptor number or inheritability is mutated, and
all Python-created originals/scratches are CLOEXEC, so concurrent unrelated
process-launch activity cannot inherit them or observe a remap window. A
common process-launch lock is therefore neither required nor authorized. Each
launch owns disjoint descriptors until spawn returns; closing another launch's
descriptor is forbidden. Mutation/substitution of `os.posix_spawn`, any spawn
constant, action ordering, scratch allocator, or `setsid` behavior rejects at
the runtime-policy boundary.

All readiness launches reachable while this bounded operation runs were
enumerated. `run_phase3b_controller`, `run_phase3b_worker`, and
`_run_preparation_worker` in `runtime.py` use this one atomic spawn owner for
the bounded generation. The bounded tool/Git launcher in `git_state.py` may run
concurrently but does not participate in FD mapping; Python's non-inheritable
default and the governed launch's CLOEXEC originals/scratches prevent it from
receiving them. No other production launch owner is reachable from this
generation. Consequently comprehensive launch serialization would add no
safety and is prohibited; the acceptance race test must exercise the existing
concurrent `git_state.py` bounded-process path explicitly.

The legacy runtime contract's `cwd_policy: detached_source_root` remains
unchanged for every legacy generation. Only
`ADAPTER_V4_EXPERIMENT5_BOUNDED_STREAMING` selects bounded launch policy literal
`cwd_policy: "cwd-ignored-absolute-fd-authority-v1"`. Darwin
`os.posix_spawn` inherits the supervisor's cwd and exposes no chdir file action;
the bounded generation therefore assigns inherited cwd no authority. Every
executable and bootstrap script path is absolute, the request is FD-backed,
source/dependency roots are absolute and identity-authenticated, Seatbelt rules
are rendered from absolute paths, Python uses `-I`, and bootstrap removes all
script/cwd entries before governed imports. Neither controller nor worker may
call `getcwd` to derive authority or resolve a trust-bearing relative path.
Changing cwd before spawn must not change command, import, request, source, or
output authority. No global `chdir`, cwd lock, or cwd fallback is permitted.

A worker does not learn any governed descriptor from environment, request
material, or a worker-selected value. `/usr/bin/time`, `sandbox-exec`, and
Python preserve exactly destinations 3 through 6 across exec. The controller
closes its copies of the read gate and worker-only endpoints immediately after
successful launch; the measurement wrapper necessarily retains its inherited
copies until it exits and never reads or writes them. The sandbox transition
retains them only until same-process exec. Python closes descriptor 3 after
gate consumption, descriptor 6 after its one bounded request read, descriptor
4 at orderly reservation-session EOF, and descriptor 5 only at worker exit.
Kernel process exit closes every remaining copy on failure. No scratch, source
original, save descriptor, controller gate-write endpoint, controller
reservation endpoint, alternate descriptor, environment variable,
command-line descriptor number, or fallback gate is worker-visible.

The release protocol is exactly byte `0xa5` followed by EOF. After launch the
controller writes exactly that one byte to its pipe endpoint and closes it.
The worker performs bounded reads totaling at most two bytes until EOF and
accepts only the one-byte string `b"\xa5"`; zero bytes, premature EOF, another
byte value, a second or trailing byte, more than one byte, or read failure is a
gate rejection. Acceptance consumes the release once, and the worker closes
descriptor 3 permanently before opening or parsing descriptor 6. A second
read, replay, descriptor reuse, or controller close without the release byte
rejects. Worker close or exit before consumption fails the invocation. The
start gate is not a reservation channel and carries no JSON, newline, identity,
path, or variable-length material.

The state machine is exactly `CREATED -> INHERITED -> WORKER_BLOCKED ->
PROCESS_AUTHORITY_VERIFIED -> RELEASED -> CONSUMED -> CLOSED`. Before
`CONSUMED`, worker code may initialize only fixed interpreter/runtime machinery,
verify that descriptor 3 is a pipe read endpoint, and perform the bounded gate
read. It may not read or parse request, configuration, descriptor, source,
projection, external-input, or reservation material. No state transition may
skip `PROCESS_AUTHORITY_VERIFIED`. Failures are closed codes
`START_GATE_MISSING`, `START_GATE_PROTOCOL_REJECTED`,
`START_GATE_PREMATURE_EOF`, `START_GATE_REUSED`, or the existing
`RESOURCE_PROCESS_INSTANCE_MISMATCH`; they contain no raw exception, descriptor
number, argv, path, or input excerpt and establish no partial authority.

The controller constructs launch vectors in
`reconstruct_bounded_streaming_launch_authority` in `runtime.py` only from the
authenticated runtime contract, authenticated Source-S worker closure,
controller-rendered authenticated Seatbelt profile, selected frozen generation
and profile authority, and controller-owned private artifacts. It performs no
shell invocation, globbing, `PATH` lookup, caller flag insertion, or
environment-variable substitution. String material is strict Unicode with no
NUL and is passed as the exact ordered `os.posix_spawn` argv tuple.
The worker wrapper vector is exactly:

```text
("/usr/bin/time", "-l", "/usr/bin/sandbox-exec", "-p",
 <exact rendered authenticated profile>, <exact authenticated Python path>,
 "-I", "-S", <exact authenticated bootstrap-script path>,
 "--governed-fixed-fds-v1")
```

After the permitted exec transition the governed-worker argv is exactly the
suffix beginning with the authenticated Python path. There are no other
arguments. Generation, execution profile, operation ID, and reservation-policy
authority are not argv: they are fields of the already authenticated closed
request bytes on descriptor 6 and must equal the controller's selected
authority before release. The analogous controller vector omits
`sandbox-exec`, `-p`, and the profile and otherwise uses the exact controller
bootstrap script and the same fixed control argument.

Before launch, the controller creates the request as canonical JSON in an
exclusive mode-0600 regular file beneath the operation-private root, keeps an
`O_RDONLY|O_NOFOLLOW` descriptor, fsyncs it, and authenticates its device,
inode, mode, owner, byte count, SHA-256, request identity, operation ID,
generation, and profile binding. Descriptor 6 is a duplicate of that verified
open file description positioned at byte zero; the pathname is not passed to
the worker and unlink/rename cannot substitute its bytes. Governed-host CPython
provides `os.pread`; a direct probe confirmed that positional reads return the
requested bytes without changing the shared open-file-description offset. The
controller hashes only bounded `os.pread(fd, chunk_size, offset)` chunks from
offset zero through exact `st_size`, rejects short, extra, or inconsistent
data, and requires `os.lseek(fd, 0, os.SEEK_CUR) == 0` before and after
authentication. Immediately before gate release it repeats `fstat`, positional
byte-count, SHA-256, bootstrap-request-identity, and generation/profile/
operation checks. It never calls ordinary `read` or changes the offset. Because
the gate remains closed, the worker cannot race these reads.

After closing the consumed gate, the worker authenticates FD 6 type, read-only
access, owner, mode, device, inode, size, and stability, requires current offset
exactly zero, and reads exactly `st_size` bounded bytes once. Early EOF, bytes
beyond the authenticated size, nonzero initial offset, metadata change, or
content/identity mismatch rejects. It rechecks `fstat` after the read, requires
the offset exactly at authenticated EOF, closes FD 6 permanently, and never
reopens a path or seeks to another position. Any mismatch rejects without
governed processing.

All five governed roles execute one shared script,
`src/orev3/execution/bounded_streaming_worker_bootstrap.py`. Its sole parser is
`bootstrap_parse_request_bytes` in that file. Its other local canonical
functions are exactly `bootstrap_validate_value`, `bootstrap_canonical_bytes`,
and `bootstrap_domain_identity`; no worker script may implement or select
another parser, encoder, or identity function. The bootstrap script is itself
authenticated from Source S by the script rules below. It imports exactly
`os`, `sys`, `fcntl`, `stat`, `hashlib`, `json`, and `unicodedata` before the gate, contains no
`orev3` or dependency import, does not inspect the working directory, and may
only validate fixed descriptors and consume the gate. Any other pre-gate import
or module-level project execution rejects static closure review and the
governed-host sentinel test.

FD 6 contains exactly one no-terminal-newline canonical JSON bootstrap envelope
of at most `MAX_BOUNDED_STREAMING_BOOTSTRAP_REQUEST_BYTES = 4194304` bytes. Its
closed top-level fields are exactly `schema_version` (integer 1),
`request_kind` (one of `phase3b_controller`, `phase3a_validator`,
`input_projector`, `readiness_test`, `replay_preparation`), `operation_id`,
`authority_generation`, `execution_profile_identity`,
`runtime_contract_identity`, `source_root_authority`,
`dependency_root_authority`, `runtime_bundle_authority`,
`worker_entrypoint_identifier`,
`worker_code_closure_identity`, `worker_request_byte_count`,
`worker_request_sha256`, `worker_request_canonical_json`, and
`bootstrap_request_identity`. No JSON null occurs anywhere in this envelope.

`source_root_authority` is the closed object with exact fields `absolute_root`,
`source_commit`, `root_tree_git_object_identity`, and
`source_code_closure_manifest`. The manifest representation and identity are
frozen below; an aggregate identity without its ordered member material is not
valid bootstrap authority.

`dependency_root_authority` is one exact tagged union. Absence is represented
only as `{"present":false}`. Presence is represented only as the closed object
with fields `present` (boolean true), `absolute_root`,
`closed_dependency_root_identity`, and `closed_dependency_root_material`.
Null, omission, an empty-string sentinel, `present:false` with another field,
and `present:true` without every presence field reject. The closed material is
the exact existing `runtime.construct_closed_dependency_root` identity material:
`root_format` equal to `wheel-projection-v1`, ordered `artifacts`, ordered
`distributions`, and ordered `files`; no alternate dependency-manifest dialect
is introduced.

`runtime_bundle_authority` is the closed object with exact fields
`runtime_bundle_identity`, `python_executable_path`, `stdlib_roots`,
`dynamic_library_roots`, and `runtime_bundle_material`. Current `runtime.py`
has no material-returning constructor; the bounded implementation therefore
adds exactly `construct_bounded_streaming_runtime_bundle_material` to
`src/orev3/execution/runtime.py`. It returns the exact material already formed
internally by existing `reconstruct_runtime_bundle_identity`:
`executable_sha256`, ordered `files`, and closed `python` material. The existing
function is not renamed or reinterpreted. The new constructor and
`reconstruct_runtime_bundle_identity` must produce, respectively, material and
identity such that `domain_identity(RUNTIME_BUNDLE_DOMAIN, material)` equals the
existing reconstruction for the same interpreter. It is not a claimed identity
standing alone.

`operation_id` has the frozen `op-` plus 32-lowercase-hex grammar;
`authority_generation` is exactly the bounded generation literal;
`execution_profile_identity`, `runtime_contract_identity`, every tree/closure/
environment/runtime-bundle identity, `worker_request_sha256`, and
`bootstrap_request_identity` are lowercase 64-hex strings. Root values are
absolute NFC paths without NUL. `worker_request_byte_count` is a true integer
in `1..1048576`; the UTF-8 worker-request string must fit that existing readiness
control-object ceiling and the
complete outer envelope must independently fit 4194304 bytes.

`worker_request_canonical_json` is a string whose strict UTF-8 encoding is the
complete canonical semantic-worker-request bytes, also without a terminal LF;
its byte count and SHA-256 must equal the two adjacent claims. It is not parsed
semantically until authenticated roots are installed and the existing trusted
request validator is imported. The bootstrap envelope identity domain is
exactly `orev3:bounded-streaming-worker-bootstrap-request:v1\n`. Its identity
material is the complete closed envelope excluding only
`bootstrap_request_identity`; thus operation, generation, profile, runtime,
source/dependency/runtime-bundle, entrypoint/closure, and payload bindings all
participate. The material fields are exactly: `schema_version`, `request_kind`,
`operation_id`, `authority_generation`, `execution_profile_identity`,
`runtime_contract_identity`, `source_root_authority`,
`dependency_root_authority`, `runtime_bundle_authority`,
`worker_entrypoint_identifier`, `worker_code_closure_identity`,
`worker_request_byte_count`, `worker_request_sha256`, and
`worker_request_canonical_json`. Canonical field ordering is provided only by
the readiness canonical ordering rules. Before project imports, the bootstrap
calls only its local `bootstrap_domain_identity`. That function requires an NFC
domain string ending in exactly one LF and computes exactly
`hashlib.sha256(domain.encode("utf-8") +
bootstrap_canonical_bytes(material)).hexdigest()`. Its
`bootstrap_canonical_bytes` produces the readiness encoding with exactly one
terminal LF; this matches the inspected formula in
`orev3.execution.canonical.domain_identity`. The FD-6 envelope itself has no
terminal LF. The controller constructs those canonical bytes and identity, FD 6 binds
that exact pair, and the worker independently parses and reconstructs the same
pair before any root installation or project import. Exact equality is
required. There is no custom worker serializer and no extension field.
The controller reconstructs and compares this identity before launch and again
through FD 6 immediately before release; the bootstrap reconstructs it before
root installation. A claimed or coordinated reseal cannot override independently
selected generation/profile/operation/root/closure authority.

`bootstrap_parse_request_bytes` performs one bounded `os.read` loop
over FD 6 only after the gate. It requires strict UTF-8 and uses `json.loads`
with an `object_pairs_hook` that rejects every duplicate, `parse_constant` that
rejects `NaN`, `Infinity`, and `-Infinity`, and `parse_float` that rejects every
float. It rejects JSON null recursively and admits only strings, lists, closed
dictionaries, booleans where the selected schema says boolean, and true Python integers—not
booleans—within each field's frozen signed/unsigned bounds before any dependent
allocation. Every key and string must be Unicode NFC, contain no NUL, and
contain no lone surrogate. It validates the exact outer and nested key sets and field types
above, plus operation-ID, generation, identity, absolute-path, payload-size,
and entrypoint finite vocabularies. It then uses
`bootstrap_canonical_bytes(value)[:-1]` as the no-LF envelope encoding and
requires byte equality. The local encoder implements the same string escaping
and integer rendering as `orev3.execution.canonical.canonical_bytes`; `json`
parsing does not establish serialization authority. Empty input,
terminal LF/CR, BOM, whitespace, reordered keys, malformed framing, trailing
bytes, or any unsupported value rejects. This parser is authority only for the
closed bootstrap envelope, not general JSON.

The local functions are not a second canonical authority. Controller-side and
post-root test authority require byte-for-byte and disposition parity over the complete
bounded envelope domain with the existing trusted readiness canonical parser:
canonical positives, malformed UTF-8, duplicate keys, whitespace/key order,
booleans versus integers, signed and unsigned edges, float/nonfinite material,
nested closed objects/arrays, missing/extra fields, and framing. Any parser or
canonical-byte disagreement stops implementation freeze. Because readiness
canonical objects carry one terminal LF while the private bootstrap artifact's
existing convention carries none, the parity oracle appends exactly one LF to
the bootstrap's canonical re-encoding and calls exactly
`orev3.execution.canonical.parse_canonical_bytes(bytes_with_lf,
max_bytes=4194305)`, compares local `bootstrap_canonical_bytes(value)` with
`orev3.execution.canonical.canonical_bytes(value)`, and compares local
`bootstrap_domain_identity(domain, material)` with
`orev3.execution.canonical.domain_identity(domain, material)`. The explicit
`4194305` is the 4,194,304-byte bootstrap
maximum plus the sole readiness framing LF; the parser's default limit is never
used. Accepted material and canonical bytes excluding that sole governed
framing difference must be identical. No other normalization is allowed.

The bootstrap-owned constant `BOUNDED_STREAMING_WORKER_DISPATCH` in
`src/orev3/execution/bounded_streaming_worker_bootstrap.py` is an immutable
five-entry map with exactly this authority:

| `worker_entrypoint_identifier` | required `request_kind` | implementation module | callable | bounded import-complete closure identifier |
| --- | --- | --- | --- | --- |
| `phase3b-controller-v1` | `phase3b_controller` | `orev3.execution.evidence_preparation_worker` | `main` | `bounded-phase3b-controller-import-closure-v1` |
| `phase3a-validator-v1` | `phase3a_validator` | `orev3.execution.preparation_worker` | `main` | `bounded-phase3a-validator-import-closure-v1` |
| `input-projector-v1` | `input_projector` | `orev3.execution.input_projection_worker` | `main` | `bounded-input-projector-import-closure-v1` |
| `readiness-test-v1` | `readiness_test` | `orev3.execution.readiness_test_worker` | `main` | `bounded-readiness-test-import-closure-v1` |
| `replay-preparation-v1` | `replay_preparation` | `orev3.execution.replay_preparation_worker` | `main` | `bounded-replay-preparation-import-closure-v1` |

These are new bounded-generation import-complete authorities, not aliases for
`PHASE3B_CONTROL_PATHS`, `PHASE3A_NORMALIZED_CODE_PATHS`, or
`WORKER_CODE_CLOSURES`; those existing tuples remain unchanged but are not
executable closure authority here. Phase-3B controller, Phase-3A validator,
readiness test, and Replay preparation use MODEL A authenticated normal-package
imports; every initializer they execute is authenticated below. Input projector
alone uses MODEL B, the initializer-suppressing bounded project import session
frozen below. Package model is fixed by entrypoint identifier and cannot be
selected per request or run.

| entrypoint | frozen package model |
| --- | --- |
| `phase3b-controller-v1` | MODEL A authenticated normal-package closure |
| `phase3a-validator-v1` | MODEL A authenticated normal-package closure |
| `input-projector-v1` | MODEL B initializer-suppressing `BoundedProjectImportSession` |
| `readiness-test-v1` | MODEL A authenticated normal-package closure |
| `replay-preparation-v1` | MODEL A authenticated normal-package closure |

The five exact ordered closure path sets are the unique paths in exactly the
order shown in the following blocks. Every role also binds the already-running
shared bootstrap path as its first separately authenticated launch member;
that bootstrap is not re-imported as project code.

`bounded-phase3b-controller-import-closure-v1`:

```text
src/orev3/__init__.py
src/orev3/execution/__init__.py
src/orev3/execution/canonical.py
src/orev3/execution/contract_validation.py
src/orev3/execution/dataset_validation.py
src/orev3/execution/evidence_preparation.py
src/orev3/execution/evidence_preparation_worker.py
src/orev3/execution/external_inputs.py
src/orev3/execution/filesystem_capability.py
src/orev3/execution/git_state.py
src/orev3/execution/phase3b_components.py
src/orev3/execution/preparation.py
src/orev3/execution/readiness.py
src/orev3/execution/readiness_candidate.py
src/orev3/execution/readiness_record.py
src/orev3/execution/registry.py
src/orev3/execution/replay_preparation.py
src/orev3/execution/runtime.py
src/orev3/execution/test_policy.py
src/orev3/execution/zero_input_phase3b.py
```

`bounded-phase3a-validator-import-closure-v1`:

```text
src/orev3/__init__.py
src/orev3/execution/__init__.py
src/orev3/execution/canonical.py
src/orev3/execution/contract_validation.py
src/orev3/execution/dataset_validation.py
src/orev3/execution/evidence_preparation.py
src/orev3/execution/external_inputs.py
src/orev3/execution/filesystem_capability.py
src/orev3/execution/git_state.py
src/orev3/execution/phase3b_components.py
src/orev3/execution/preparation.py
src/orev3/execution/preparation_worker.py
src/orev3/execution/readiness.py
src/orev3/execution/readiness_candidate.py
src/orev3/execution/readiness_record.py
src/orev3/execution/registry.py
src/orev3/execution/replay_preparation.py
src/orev3/execution/runtime.py
src/orev3/execution/test_policy.py
src/orev3/execution/zero_input_phase3b.py
```

`bounded-input-projector-import-closure-v1`:

```text
src/orev3/datasets/rq003_experiment0.py
src/orev3/execution/canonical.py
src/orev3/execution/dataset_validation.py
src/orev3/execution/filesystem_capability.py
src/orev3/execution/input_projection_worker.py
src/orev3/execution/projection.py
src/orev3/execution/replay_preparation.py
src/orev3/experiments/rq003_execution_specification.py
src/orev3/experiments/rq003_execution_specification_v2.py
src/orev3/experiments/rq003_experiment2a.py
src/orev3/experiments/rq003_experiment5.py
src/orev3/experiments/rq003_experiment5_ranking.py
src/orev3/experiments/rq003_experiment5_source_measurements.py
src/orev3/experiments/rq003_experiment5_source_processing.py
src/orev3/features/base.py
src/orev3/features/context.py
src/orev3/features/rq003_active_round_motherlode.py
src/orev3/features/rq003_contracts.py
src/orev3/features/rq003_deployed_lamports.py
src/orev3/features/rq003_execution.py
src/orev3/features/rq003_measurement_support.py
src/orev3/features/rq003_miner_count.py
src/orev3/features/rq003_production_cost_ema.py
src/orev3/features/rq003_registry.py
src/orev3/features/rq003_total_miners.py
src/orev3/features/rq003_total_vaulted.py
src/orev3/features/rq003_total_winnings.py
src/orev3/features/rq003_treasury_motherlode.py
src/orev3/features/types.py
src/orev3/historical/models.py
src/orev3/historical/reader.py
src/orev3/replay/engine.py
src/orev3/replay/loader.py
src/orev3/replay/models.py
src/orev3/strategy_lab/interfaces.py
src/orev3/strategy_lab/runner.py
```

This closure is exactly 36 lexically ordered members. Its immutable
fully-qualified-name map is exactly:

```text
orev3.datasets.rq003_experiment0 -> src/orev3/datasets/rq003_experiment0.py
orev3.execution.canonical -> src/orev3/execution/canonical.py
orev3.execution.dataset_validation -> src/orev3/execution/dataset_validation.py
orev3.execution.filesystem_capability -> src/orev3/execution/filesystem_capability.py
orev3.execution.input_projection_worker -> src/orev3/execution/input_projection_worker.py
orev3.execution.projection -> src/orev3/execution/projection.py
orev3.execution.replay_preparation -> src/orev3/execution/replay_preparation.py
orev3.experiments.rq003_execution_specification -> src/orev3/experiments/rq003_execution_specification.py
orev3.experiments.rq003_execution_specification_v2 -> src/orev3/experiments/rq003_execution_specification_v2.py
orev3.experiments.rq003_experiment2a -> src/orev3/experiments/rq003_experiment2a.py
orev3.experiments.rq003_experiment5 -> src/orev3/experiments/rq003_experiment5.py
orev3.experiments.rq003_experiment5_ranking -> src/orev3/experiments/rq003_experiment5_ranking.py
orev3.experiments.rq003_experiment5_source_measurements -> src/orev3/experiments/rq003_experiment5_source_measurements.py
orev3.experiments.rq003_experiment5_source_processing -> src/orev3/experiments/rq003_experiment5_source_processing.py
orev3.features.base -> src/orev3/features/base.py
orev3.features.context -> src/orev3/features/context.py
orev3.features.rq003_active_round_motherlode -> src/orev3/features/rq003_active_round_motherlode.py
orev3.features.rq003_contracts -> src/orev3/features/rq003_contracts.py
orev3.features.rq003_deployed_lamports -> src/orev3/features/rq003_deployed_lamports.py
orev3.features.rq003_execution -> src/orev3/features/rq003_execution.py
orev3.features.rq003_measurement_support -> src/orev3/features/rq003_measurement_support.py
orev3.features.rq003_miner_count -> src/orev3/features/rq003_miner_count.py
orev3.features.rq003_production_cost_ema -> src/orev3/features/rq003_production_cost_ema.py
orev3.features.rq003_registry -> src/orev3/features/rq003_registry.py
orev3.features.rq003_total_miners -> src/orev3/features/rq003_total_miners.py
orev3.features.rq003_total_vaulted -> src/orev3/features/rq003_total_vaulted.py
orev3.features.rq003_total_winnings -> src/orev3/features/rq003_total_winnings.py
orev3.features.rq003_treasury_motherlode -> src/orev3/features/rq003_treasury_motherlode.py
orev3.features.types -> src/orev3/features/types.py
orev3.historical.models -> src/orev3/historical/models.py
orev3.historical.reader -> src/orev3/historical/reader.py
orev3.replay.engine -> src/orev3/replay/engine.py
orev3.replay.loader -> src/orev3/replay/loader.py
orev3.replay.models -> src/orev3/replay/models.py
orev3.strategy_lab.interfaces -> src/orev3/strategy_lab/interfaces.py
orev3.strategy_lab.runner -> src/orev3/strategy_lab/runner.py
```

Every member is necessary for the following closed reason; none is present for
directory breadth:

| member/module group | exact role necessity |
| --- | --- |
| `datasets.rq003_experiment0` | Supplies the governed square/dataset primitives transitively required by Experiment-005 source material. |
| `execution.canonical` | Canonical parsing, validation, and identity primitives used after authenticated import. |
| `execution.dataset_validation` | Constructs the governed dataset-validation result. |
| `execution.filesystem_capability` | Enforces authenticated file/output capability operations. |
| `execution.input_projection_worker` | Exact mapped role entrypoint. |
| `execution.projection` | Defines projection reconstruction and evidence primitives. |
| `execution.replay_preparation` | Supplies the bounded projection-to-Replay contract used by projection validation. |
| `experiments.rq003_execution_specification` and `_v2` | Define the frozen RQ-003 execution/profile contracts consumed transitively by Experiment 005. |
| `experiments.rq003_experiment2a` | Supplies the inherited governed experiment material referenced by Experiment-005 definitions. |
| `experiments.rq003_experiment5` | Defines Experiment-005 configuration/scientific material. |
| `experiments.rq003_experiment5_ranking` | Supplies the frozen ranking material referenced by Experiment-005 source processing. |
| `experiments.rq003_experiment5_source_measurements` | Constructs the exact source measurement vector. |
| `experiments.rq003_experiment5_source_processing` | Owns the bounded source decoder/index/round projection algorithm. |
| `features.base` | Defines the feature protocol used by governed RQ-003 features. |
| `features.context` | Defines the authenticated observation context. |
| `features.rq003_contracts` | Defines RQ-003 canonical feature and metadata contracts. |
| `features.rq003_registry` | Defines the frozen finite feature registry material. |
| `features.rq003_measurement_support` | Shared bounded measurement validation used by every selected feature. |
| `features.rq003_execution` | Constructs the fixed ordered RQ-003 measurement pipeline. |
| `features.rq003_active_round_motherlode` | Exact selected active-round-motherlode measurement. |
| `features.rq003_deployed_lamports` | Exact selected deployed-lamports measurement. |
| `features.rq003_miner_count` | Exact selected miner-count measurement. |
| `features.rq003_production_cost_ema` | Exact selected production-cost EMA measurement. |
| `features.rq003_total_miners` | Exact selected total-miners measurement. |
| `features.rq003_total_vaulted` | Exact selected total-vaulted measurement. |
| `features.rq003_total_winnings` | Exact selected total-winnings measurement under the already-frozen source whitelist. |
| `features.rq003_treasury_motherlode` | Exact selected treasury-motherlode measurement. |
| `features.types` | Defines feature snapshot/value types required by the selected features. |
| `historical.models` | Defines replay/historical record shapes consumed by source reconstruction. |
| `historical.reader` | Supplies authenticated historical-record reading required transitively by Replay material. |
| `replay.models` | Defines Replay unit and observation shapes. |
| `replay.loader` | Supplies bounded Replay record loading primitives used by the governed path. |
| `replay.engine` | Supplies deterministic Replay ordering/state primitives required by the selected source flow. |
| `strategy_lab.interfaces` | Defines only the decision/ranking interfaces used by measurement construction. |
| `strategy_lab.runner` | Defines the experiment configuration/runner types referenced by the exact Experiment-005 contract. |

Each combined row names every literal module it justifies. Removing any listed
member makes the governed representative import/startup trace fail; importing
another project member is not a permitted repair.

There are no aliases, wildcard entries, directory entries, or runtime-added
members. In particular, initializer-only `datasets.square_features`,
`features.pipeline`, `features.raw`, `features.registry`, `features.relative`,
`features.temporal`, and the `strategy_lab` constraints, deployment, economic,
evaluation, experiment, materialization, metrics, readiness, registry,
settlement, strategies, and transactions graph are excluded and must not
execute. This avoids granting outcome, settlement, transaction, or unrelated
strategy code merely because those real initializers exist.
This prerequisite authorizes no change to
`src/orev3/datasets/__init__.py`, `src/orev3/features/__init__.py`,
`src/orev3/strategy_lab/__init__.py`, or consumers of their public re-exports.
The broader package-refactor model is rejected for this prerequisite.

For this role only, `bounded_streaming_worker_bootstrap.py` owns exact classes
`BoundedProjectImportSession`, `BoundedProjectMetaPathFinder`, and
`AuthenticatedBoundedProjectSourceLoader`, plus closed failure
`BoundedProjectImportError`. After complete manifest authentication and before
any project import, the session snapshots every `sys.modules` entry whose key
is `orev3` or starts with `orev3.`, preserving both the complete key set and
each exact object reference, then removes every such entry.

MODEL-B import-session exclusivity is the single-threaded worker invariant.
The same bootstrap owns exact helper
`assert_bounded_project_import_session_single_threaded`. On the governed Darwin
24.0.0 arm64 / CPython 3.14.5 runtime, the complete Python-thread census is the
exact mapping returned by `sys._current_frames()`. The helper obtains
`current_ident = threading.get_ident()`, requires the census to be a mapping
whose keys are integers and whose values are frame objects, and accepts only
when its exact key set is `{current_ident}`. `threading.enumerate()` may be
recorded in tests as non-authoritative diagnostic material but is never the
census: governed-host probes showed that it omitted live raw and joinable
`_thread` workers that `sys._current_frames()` reported.

This census proves exactly that the current thread is the sole thread with a
current Python frame and therefore the sole thread then capable of executing
Python code in this interpreter. It makes no native-process single-threading
claim. Native threads with no Python thread state and no ability to execute
Python mutation of `sys.modules`, `sys.meta_path`, or session state are outside
this authority. A census exception, non-mapping, malformed key/value, absent
current identifier, or additional identifier produces
`BOUNDED_PROJECT_IMPORT_SESSION_INTEGRITY`. No frame, thread identifier, stack,
or name enters diagnostics. The terminal disposition below applies; such a
failure never falls through to generic cleanup.

The complete governed CPython 3.14.5 Python-visible thread-start attribute set
is frozen as `threading.Thread.start`, `threading._start_joinable_thread`,
`_thread.start_new_thread`, `_thread.start_new`, and
`_thread.start_joinable_thread`. `threading._start_joinable_thread` and
`_thread.start_joinable_thread` are the same callable object on this runtime;
`_thread.start_new` and `_thread.start_new_thread` are distinct callable
objects despite the former being documented as an obsolete synonym. Every
listed attribute is captured, patched, verified, and restored independently,
including both names of an alias. `threading.Timer.start` inherits
`threading.Thread.start`, and `ThreadPoolExecutor` worker creation reaches the
same patched standard or low-level primitives; neither establishes an
additional unpatched authority.

Denial installation is exact: run the complete census and require only
`current_ident`; capture the exact original object at each of the five
attributes; replace every attribute with its own recorded session-owned denial
callable; require each attribute to reference its exact denial object by `is`;
immediately rerun the complete census; and only after that second census passes
may any `sys.modules`, synthetic-shell, `sys.meta_path`, or bounded-session
mutation begin. Each denial callable creates no thread, returns no handle, and
raises `BoundedProjectImportError` carrying only
`BOUNDED_PROJECT_IMPORT_SESSION_INTEGRITY`. It does not expose arguments,
target, thread name, path, or underlying exception material.

The second census closes rather than denies scheduling in the installation
window: if another thread starts after the first census but before all denials
are installed, either a denial prevents it or the second census observes it;
no project/global import mutation has yet occurred. Mathematical atomicity is
not claimed. At every later integrity checkpoint, each of the five attributes
must still reference its exact installed denial object. Replacement, deletion,
early restoration, alias mutation, or any foreign callable is a closed failure.

Complete census and denial-integrity checks run immediately after denial
installation; after Model-B setup; before the first governed project import;
before semantic processing; before trusted result return; before cleanup;
after global project-import state is restored but before denial restoration;
and after exact denial restoration. Any failure makes the result untrusted and
uses the terminal disposition below rather than in-process restoration. Static
review of all 36 current members found no
`threading`, `_thread`, executor, `Thread`, or thread-start use. The
authenticated dependency startup/processing path for this role must likewise
show no intentional Python-thread creation. Governed dynamic startup tracing
must confirm the census remains singular; a closure or dependency that creates
a Python thread is incompatible and requires renewed governance, not an
exception.

Current governed-host feasibility evidence imported the only third-party root
directly present in the 36-member import graph, `pydantic` 2.13.4, under CPython
3.14.5: the complete census contained one identifier before and after import,
and `threading.enumerate()` likewise contained one entry. This is feasibility
evidence, not a substitute for the future full-role dynamic acceptance trace.

Before finder installation the session also snapshots the complete
`sys.meta_path` as an ordered tuple of exact object references. The only
permitted session change is insertion of the one session finder at index zero;
the original objects must remain at indexes one onward in their original order.
No project or dependency code may insert, remove, replace, or reorder a finder.
Integrity checks require exact length, ordering, and `is` identity after setup,
before and after every governed project load, before semantic processing,
before result return, and before cleanup.

The session constructs exactly eight inert package shells: `orev3`,
`orev3.datasets`, `orev3.execution`, `orev3.experiments`, `orev3.features`,
`orev3.historical`, `orev3.replay`, and `orev3.strategy_lab`. Each shell has
`__name__` and `__package__` equal to its exact name, `__loader__ = None`, and
`__path__` equal to the one-element list containing its authenticated package
directory. Its `__spec__` is exactly
`importlib.machinery.ModuleSpec(name, loader=None, is_package=True)` with
`submodule_search_locations` set to that same one authenticated directory.
Shells have no initializer execution, forwarding, lazy `__getattr__`, exports,
or side effects; normal child-module attributes may be attached only by Python
when an authenticated mapped child loads.

Installation order is fixed: authenticate the complete 36-member manifest;
construct and compare the literal name/path map; run the complete census;
capture and install all five thread-start denials; verify every hook by object
identity; rerun the complete census; snapshot and remove the project cache;
snapshot the complete meta path; construct and insert the eight shells;
construct the finder and loader; insert the finder at `sys.meta_path[0]`; verify
census/hook/cache/meta-path integrity; import the mapped input-worker module;
execute the role; and apply the exact ordinary-versus-terminal disposition
below. No project/global import state changes before the post-install census
passes. During the session, the only `orev3`-domain cache entries are those
eight shells and mapped loaded modules.

The exact mutation state machine is `PRE_MUTATION ->
GLOBAL_INTERPRETER_STATE_MUTATED`. `PRE_MUTATION` ends irreversibly at the first
replacement of any of the five thread-start attributes or the first mutation
of the `orev3`-domain `sys.modules` mapping, synthetic-shell state,
`sys.meta_path`, bounded finder, or session object, whichever occurs first.
Thus no project import has occurred in `PRE_MUTATION`, and every project/global
import-state mutation occurs only in `GLOBAL_INTERPRETER_STATE_MUTATED`.

Loss of exclusivity is terminal in both states. In `PRE_MUTATION`, a census
that does not prove the sole current thread terminates immediately; it does not
install or restore hooks and does not mutate project cache, meta path, shells,
finder, or session state. This uniform rule avoids a second pre-mutation
recovery authority. In `GLOBAL_INTERPRETER_STATE_MUTATED`, an additional
Python thread, census exception or malformed result, missing current thread,
or inability to prove the exact singleton census makes in-process
interpreter-global restoration untrusted. Joining, waiting for, or re-censusing
after an unexpected thread; restoring after it exits; retrying cleanup; or
continuing semantic processing is forbidden.

The exact non-returning terminal primitive is `os._exit(70)`, invoked by the
worker immediately after detecting a terminal condition. Exit status 70 is the
dedicated `BOUNDED_PROJECT_IMPORT_SESSION_INTEGRITY` transport status for this
bounded generation: status 0 is success, existing ordinary governed worker
validation/resource statuses occupy 2 through 11, and 70 cannot be interpreted
as any of them. Governed-host evidence under Darwin 24.0.0 / CPython 3.14.5
confirmed that `os._exit(70)` bypasses Python `finally` and `atexit` execution
and that authenticated `/usr/bin/time -l` propagates status 70.

After selecting this terminal path, the worker sets no Python global, emits no
diagnostic or result payload, performs no cache, meta-path, shell, finder,
session, project, descriptor, or thread-hook cleanup, and calls `os._exit(70)`
immediately. Process exit closes inherited descriptors. Thread-start hooks,
project cache, and meta-path state are not restored in that interpreter because
the entire worker process terminates. Exact in-process restoration remains
mandatory only for ordinary success or failure while every complete census
proves the sole current thread.

A denial-hook deletion, replacement, premature restoration, alias mutation,
or foreign callable triggers an immediate complete census. Hook-integrity loss
is terminal through `os._exit(70)` even when that census is singular, because
thread creation may no longer be prevented. If another thread exists or the
census cannot prove singularity, the same path applies. A cache or meta-path
integrity failure may use ordinary exact cleanup only when the census proves
the sole current thread and all five denial hooks remain intact; otherwise it
uses `os._exit(70)`.

The worker constructs or transmits a trusted result only after the final
census, all five hook-identity checks, complete project-cache integrity, and
exact meta-path integrity pass, in that order. No earlier success bytes or
outstanding acknowledgment can become trusted. `os._exit(70)` closes worker
IPC and may present EOF to the controller, but the controller waits for and
decodes the authenticated invocation status before classifying EOF or accepting
any output. Wrapper status 70 takes precedence over EOF, truncated protocol,
or buffered candidate output and maps deterministically to
`BOUNDED_PROJECT_IMPORT_SESSION_INTEGRITY`; no worker payload is required or
accepted on that path.

The controller then trusts no worker result or private projection, performs no
semantic retry in the same operation, and invalidates the bounded worker
attempt. Remaining cleanup is entirely controller-owned under existing
authority: confirm the worker is dead, authenticate and terminate remaining
invocation-group roles if required by the frozen process rules, close
controller-owned descriptors, reconcile reservations conservatively, recover
or remove the private operation root under the existing lock/recovery model,
and publish no partial output. It never attempts to reconstruct worker Python
objects or interpreter state.

The existing `GovernedSpawnHandle` remains the sole wait/reap owner. It reaps
the authenticated `/usr/bin/time` wrapper exactly once through the frozen
`os.waitpid` loop, verifies process identity, and decodes propagated exit status
70. There is no competing reaper. Because the unexpected Python thread shares
the governed Python process, `os._exit(70)` terminates that whole process; no
thread-specific signal is used. Existing authenticated process-group cleanup
handles any remaining wrapper role and otherwise remains unchanged.

When each shell or mapped module is created, the session retains its exact
object reference. Every integrity checkpoint requires the complete current
`orev3`/`orev3.*` mapping to contain only the eight shells plus the authorized
loaded subset of the 36 mapped modules, and requires every present authorized
key to reference its recorded session object by `is`. An unauthorized key,
deleted shell, replacement shell/module, or forged object under an authorized
but not-yet-loaded name is a closed integrity failure.

`BoundedProjectMetaPathFinder` is the sole resolver for `orev3` names during
the session. It recognizes shell names only as the already-installed inert
shells, returns an exact authenticated loader spec only for a mapped module,
and raises `BoundedProjectImportError` (a `ModuleNotFoundError` subclass) for
every other `orev3` name. It never returns `None` for an unauthorized project
name, so no later finder, working tree, editable installation, ambient path, or
current directory can satisfy it. It does not claim non-`orev3` names.

Immediately before compilation, `AuthenticatedBoundedProjectSourceLoader`
reopens the exact mapped member descriptor-relatively from the authenticated
Source-S root, rejects symlink or escape, requires regular mode 100644, and
recomputes byte count, SHA-256, and the governed SHA-1 Git blob identity. Only
exact manifest equality permits strict UTF-8 decoding, compilation of those
exact bytes, and execution under the exact mapped name. Ordinary builtins are
available: this is a project-origin guard, not a general Python or stdlib
sandbox. Authenticated dependency and runtime/stdlib imports continue through
their already-governed ordinary finders and roots.

Python resolves relative imports using the authenticated importing module's
`__package__`, `__spec__`, and inert shell hierarchy. Any resulting `orev3`
name returns through the same finder and must be mapped before source execution;
relative escape rejects. The general Source-S `src` directory is not placed on
`sys.path` for project resolution. Project resolution is exclusively finder-
driven; dependency and authenticated runtime roots remain on `sys.path` only
for their respective non-project authorities.

After every project load, the session verifies exact module name, authenticated
manifest origin in `__file__` and `__spec__.origin`, exact bounded-loader
identity, and current-session ownership. This is defense in depth after the
pre-execution decision. Missing members reject without adding, scanning, or
retrying authority.

Ordinary in-process cleanup is mandatory after success,
compilation/import/module-execution failure, or semantic failure only while the
complete census still proves the sole current thread and all five denial hooks
remain intact. It stops trusted semantic progression; runs the
complete census and hook-integrity check; disables further session imports;
removes the finder by exact object identity after exact current meta-path-shape
verification; requires the resulting `sys.meta_path` length, order, and every
object reference to equal the pre-session tuple; removes every session-created
`orev3` module and shell; restores every preexisting project-cache key to its
original object reference; and requires the complete resulting project-domain
key/object mapping to equal the pre-session snapshot. It then verifies all five
denial hooks are still intact, reruns the complete census, restores every one of
the five original thread-start attributes to its captured object by exact
identity, verifies each restored object by `is`, performs the final complete
census, and verifies no finder, loader, shell, denial callable, or session
authority remains installed. Thread-start ability is never restored before
global project-import state is proven clean. It never overwrites an unexplained
foreign meta-path mutation and continues: such a mismatch is a hard cleanup
failure. Inability to restore any original thread-start callable, cache object,
or meta-path object exactly is a complete worker/controller failure with no
trusted projection or evidence and no semantic continuation.
Dependency and stdlib caches are outside this narrowly scoped snapshot and
remain governed by their authenticated roots and the fresh worker process.

The normal CPython import lock operates normally for individual imports but is
not authority for the multi-step session lifecycle. Closure comes from the
complete Python-frame census, complete thread-start denial, exact
project-cache ownership, and exact meta-path snapshot/integrity/restoration;
no additional general import-lock subsystem is introduced.

Extra Python threads, unauthorized/replaced project-cache objects, any
meta-path mutation, or a missing/replaced session finder produce exact closed
failure code `BOUNDED_PROJECT_IMPORT_SESSION_INTEGRITY`. Diagnostics contain
only that code and the already-governed operation/session identity; they contain
no thread name, module object or repr, path, arbitrary exception text,
`sys.path`, `sys.meta_path`, or cache dump. Cache/meta-path failures with a
proven singular census and intact hooks enter ordinary cleanup; census or hook
failure uses the non-returning status-70 path without worker diagnostics. Both
paths trust no output, and ordinary cleanup fails completely if exact
restoration cannot be established.

`bounded-readiness-test-import-closure-v1`:

```text
config/research/readiness/adapter-registry-v1.json
config/research/readiness/attempt-authority-contract-v1.json
pyproject.toml
src/orev3/__init__.py
src/orev3/execution/__init__.py
src/orev3/execution/attempts.py
src/orev3/execution/canonical.py
src/orev3/execution/contract_validation.py
src/orev3/execution/control_storage.py
src/orev3/execution/dataset_validation.py
src/orev3/execution/evidence_preparation.py
src/orev3/execution/external_inputs.py
src/orev3/execution/filesystem_capability.py
src/orev3/execution/git_state.py
src/orev3/execution/orchestrator.py
src/orev3/execution/outcome_gate.py
src/orev3/execution/phase3b_components.py
src/orev3/execution/preparation.py
src/orev3/execution/readiness.py
src/orev3/execution/readiness_candidate.py
src/orev3/execution/readiness_record.py
src/orev3/execution/readiness_test_worker.py
src/orev3/execution/registry.py
src/orev3/execution/replay_preparation.py
src/orev3/execution/runtime.py
src/orev3/execution/test_policy.py
src/orev3/execution/zero_input_phase3b.py
src/orev3/execution/schemas/v1/adapter-declaration-v3.schema.json
src/orev3/execution/schemas/v1/adapter-registry.schema.json
src/orev3/execution/schemas/v1/artifact-declaration-evidence.schema.json
src/orev3/execution/schemas/v1/attempt-allocation.schema.json
src/orev3/execution/schemas/v1/attempt-authority-contract.schema.json
src/orev3/execution/schemas/v1/attempt-control-record.schema.json
src/orev3/execution/schemas/v1/attempt-identity-material.schema.json
src/orev3/execution/schemas/v1/dataset-validation-evidence.schema.json
src/orev3/execution/schemas/v1/evidence-preparation-policy.schema.json
src/orev3/execution/schemas/v1/evidence-preparation-v2.schema.json
src/orev3/execution/schemas/v1/execution-control-manifest.schema.json
src/orev3/execution/schemas/v1/immutable-input-snapshot.schema.json
src/orev3/execution/schemas/v1/implementation-binding.schema.json
src/orev3/execution/schemas/v1/launch-authority-snapshot.schema.json
src/orev3/execution/schemas/v1/offline-artifact-manifest.schema.json
src/orev3/execution/schemas/v1/outcome-authorization.schema.json
src/orev3/execution/schemas/v1/outcome-blind-projection-evidence.schema.json
src/orev3/execution/schemas/v1/output-namespace-identity-material.schema.json
src/orev3/execution/schemas/v1/population-accounting-evidence-v2.schema.json
src/orev3/execution/schemas/v1/profile-conformance-evidence-v2.schema.json
src/orev3/execution/schemas/v1/profile-contract.schema.json
src/orev3/execution/schemas/v1/readiness-failure-receipt.schema.json
src/orev3/execution/schemas/v1/readiness-record-v2.schema.json
src/orev3/execution/schemas/v1/readiness-test-evidence.schema.json
src/orev3/execution/schemas/v1/readiness-test-policy-v2.schema.json
src/orev3/execution/schemas/v1/replay-evidence-v2.schema.json
src/orev3/execution/schemas/v1/repository-authority.schema.json
src/orev3/execution/schemas/v1/runtime-contract.schema.json
src/orev3/execution/schemas/v1/source-scope.schema.json
tests/execution/test_attempts.py
tests/execution/test_control_storage.py
tests/execution/test_orchestrator.py
tests/execution/test_outcome_gate.py
tests/execution/test_phase3c_schema_registry.py
tests/execution/test_readiness_mandatory_v1.py
```

The non-Python configuration/schema paths above are read authority, not import
origins, and use `test_configuration` file kind. There is no applicable
`conftest.py` or test helper in this exact closure. The
six test paths are exactly the bounded generation's adopted
`readiness-test-policy-v2.json` `required_selectors`; `launch_smoke_selectors`
and additional selectors are empty. The semantic request may contain only the
whole-file selector or an exact collected node ID whose path is one of those
six files and whose node ID belongs to the independently reconstructed frozen
302-node collection. Arbitrary paths, globbing, traversal, another conftest,
unmanifested helper, or pytest node discovery outside this manifest rejects.
Before pytest import, the controller environment and worker independently
require `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`; absence or another value rejects.
The invocation retains exact `-p no:cacheprovider -p no:terminal` authority.
Only pytest's authenticated built-in plugins and dependency modules present in
the closed dependency manifest may load. Entry-point-discovered, environment-
selected, command-line-selected, local `conftest.py`, and arbitrary external
plugins are prohibited; `PYTEST_PLUGINS`, `PYTEST_ADDOPTS`, and every other
plugin-selection environment variable are absent. The worker rejects an
unexpected registered plugin origin before collection.

`bounded-replay-preparation-import-closure-v1`:

```text
src/orev3/__init__.py
src/orev3/execution/__init__.py
src/orev3/execution/canonical.py
src/orev3/execution/filesystem_capability.py
src/orev3/execution/replay_preparation.py
src/orev3/execution/replay_preparation_worker.py
```

The bounded governance implementation owns these five literal tuples in
`bounded_streaming_worker_bootstrap.py`. Governance-design closure reconstruction
recursively followed every syntactic repository-owned import from each entry
module and, for readiness tests, every selected test. Runtime import tracing is
acceptance evidence only and cannot add a member. Module, callable, closure identifier, request
kind, and entrypoint identifier are inseparable. The map has exactly these five
keys and values; an unknown key, extra entry, alias, substituted callable,
module, closure, or coordinated map/envelope substitution rejects before any
project import.

The `source_code_closure_manifest` is a closed object with exact fields
`schema_version` (integer 1), `source_closure_identifier`, `source_commit`,
`root_tree_git_object_identity`, `git_object_format` (literal `"sha1"`), `members`, and
`source_code_closure_manifest_identity`. `members` is the exact ordered tuple
selected above, represented as closed objects with fields `path`, `mode`
(`"100644"`), `file_kind`, `git_object_identity`, `byte_count`, and `sha256`.
`file_kind` is exactly `python_source` for `src/**/*.py`, `test_source` for
`tests/**/*.py`, and `test_configuration` for the explicitly listed JSON
schema/configuration members and `pyproject.toml`; no other kind is
authorized. Its identity
domain is exactly
`orev3:bounded-streaming-source-code-closure-manifest:v1\n`; its canonical
material is the complete manifest excluding only
`source_code_closure_manifest_identity`. The bootstrap recomputes each Git blob
object as `hashlib.sha1(b"blob " + str(byte_count).encode("ascii") + b"\\0" +
bytes).hexdigest()` as well as recomputing byte count and SHA-256. The current
repository object format was independently verified as `sha1`; another format
requires governance revision. A claimed closure or manifest identity alone is never byte
authority.

The outer `worker_code_closure_identity` must equal the selected manifest's
`source_code_closure_manifest_identity` exactly. There is no parallel aggregate
closure formula. The controller reconstructs both from authenticated Source S;
the worker reconstructs the manifest identity from actual verified member
material and requires the same equality before import.

Worker source verification is stdlib-only and descriptor-relative. It first
requires `absolute_root` to equal the controller-authenticated
`runtime.DetachedSource` root and the manifest commit/tree to equal the
controller-selected Source S authority. It normalizes every member path to NFC,
requires the canonical repository-relative spelling, rejects absolute paths,
empty components, `.`, `..`, backslashes, NUL, duplicates, and path escape,
and walks from a no-follow root descriptor with `os.open(..., dir_fd=...,
O_NOFOLLOW)`. Every intermediate is a real directory and every leaf a regular,
nonsymlink mode-100644 file. Bounded reads must match the manifest's byte count,
SHA-256, and Git object. Missing members reject. A manifest member not in the
dispatch tuple or a dispatch member absent from the manifest rejects; files in
the authenticated detached tree outside that role's closure do not become
import authority. The bootstrap's stdlib-only origin guard permits project
module resolution only to the authenticated closure-member paths; resolving a
same-name or additional project module outside that finite set rejects. For
input projector this means exactly `BoundedProjectMetaPathFinder` and
`AuthenticatedBoundedProjectSourceLoader` as frozen above; post-import checking
alone is not authority. The other four roles retain their previously accepted
MODEL-A import enforcement unchanged.

The present dependency object reuses, without a new identity, existing domain
`orev3:readiness-closed-dependency-root:v1\n`. The bootstrap recomputes that
identity over the supplied complete `closed_dependency_root_material`, requires
its ordered `files` to be the exact finite materialized-root population, and
descriptor-relatively verifies every file's path, regular/nonsymlink status,
byte count, and SHA-256. Its allowed importable top-level names are derived
exactly from the material's ordered `artifacts[].top_level_names`; a name not in
that closed vocabulary cannot be imported. It does not call Git, packaging,
distribution APIs, or project code. Phase-3B controller and Phase-3A validator
roles require the exact absent object `{"present":false}`; input-projector,
readiness-test, and replay-preparation roles require the exact present object.
Presence/absence substitution rejects before `sys.path` mutation.

The runtime bundle likewise reuses, without a new identity, existing domain
`orev3:readiness-python-runtime-bundle:v1\n`. The bootstrap requires the
manifest executable digest and closed Python implementation/version/cache/ABI/
platform material to match the already authenticated interpreter, recomputes
the existing runtime-bundle identity, and descriptor-relatively verifies every
ordered regular file or governed symlink entry in `runtime_bundle_material`.
Regular entries require exact count/SHA and safe mode; symlinks require the
exact request-bound target and must remain within the frozen runtime bundle.
`stdlib_roots` is exactly the ordered isolated-interpreter roots authenticated
by those entries, and `dynamic_library_roots` is exactly their governed
`lib-dynload` subset; neither list may contain an ambient, missing, duplicate,
or unmanifested root. A claimed runtime identity, interpreter path, or host
metadata alone is not filesystem byte authority.

The byte-authenticated runtime material is the interpreter executable SHA-256
and every ordered `files` entry's path, byte count, SHA-256, and governed
symlink target. The host-runtime metadata authority is exactly the closed
`python` object (`implementation`, `version`, `cache_tag`, `abi_tag`, and
`platform_tag`) reconstructed from the authenticated running interpreter using
stdlib `sys`, `platform`, and `sysconfig` only after the manifest's stdlib
authority permits those modules; the minimal built-in `sys` facts needed to
locate and authenticate that manifest may be read earlier but cannot authorize
another root. Controller construction binds all five values, and the worker
compares them after byte verification. Any disagreement rejects; no ambient
`sys.path` member becomes authority.

The five role manifests are finite. A current-HEAD canonical construction using
the exact paths above measured source-manifest sizes of 5,421 bytes for
Phase-3B, 5,410 for Phase-3A, 9,571 for input projection, 17,023 for readiness
test, and 1,877 for Replay preparation. Pre-adoption construction of the
current closed dependency projection found 6,558 non-bytecode file entries and
1,038,893 canonical manifest bytes; the runtime bundle found 2,497 entries and
378,462 canonical manifest bytes. The largest manifest combination is therefore
the readiness-test combination at 1,434,378 bytes before the bounded semantic
request and fixed outer fields. Every existing semantic request is governed by
the readiness 1,048,576-byte control-object ceiling, which remains its exact
maximum here. Exact construction of all five complete envelopes is mandatory
before adoption and each must remain at or below 4,194,304 bytes; a larger
envelope rejects rather than raising either bound. The measured manifest sizes
are feasibility evidence, not new byte membership authority; final sizes and
member identities bind the eventually approved Source S bytes.

| role | source-manifest bytes | dependency-manifest bytes | runtime-manifest bytes | fixed manifest subtotal | governed complete-envelope maximum |
| --- | ---: | ---: | ---: | ---: | ---: |
| Phase-3B controller | 5,421 | 0 | 378,462 | 383,883 | 4,194,304 |
| Phase-3A validator | 5,410 | 0 | 378,462 | 383,872 | 4,194,304 |
| Input projector | 9,571 | 1,038,893 | 378,462 | 1,426,926 | 4,194,304 |
| Readiness test | 17,023 | 1,038,893 | 378,462 | 1,434,378 | 4,194,304 |
| Replay preparation | 1,877 | 1,038,893 | 378,462 | 1,419,232 | 4,194,304 |

The final column is a hard canonical-byte maximum, not padding authority.
Controller construction measures the complete envelope—including absolute-root
strings, identities, outer keys, and the semantic request—before FD creation.
The 1,048,576-byte semantic-request maximum plus the measured largest manifest
subtotal leaves more than 1.7 MiB for those fixed outer fields; exact candidate
construction, not this arithmetic margin, is the final acceptance check.
For input projector specifically, the conservative complete current-HEAD
envelope estimate is 3,524,078 bytes. Its 36-member manifest is 9,571 bytes,
has current-HEAD feasibility identity
`5c7eb560e09274c2474db90af7f3782ebed32f2fb98fc5693d91e982dcdd1781`,
and binds current tree `a9441978900f90aeb6347ed5dd83ea0d0f274771`.
These are feasibility observations only; approved Source S must reconstruct all
member Git/SHA material and final identity independently.

The source root is created exclusively by existing `runtime.DetachedSource`:
`GitRepository.resolve_commit` followed by `git worktree add --detach
--no-checkout <root> <commit>` and `git -C <root> checkout --detach <commit>`.
The controller requires exact detached HEAD, root tree Git identity, clean
governed paths, controller ownership, non-group/non-world-writable directories,
no symlink in a governed closure path, and exact ordered path/mode/blob/SHA
closure before launch and before gate release. Cleanup uses only
`DetachedSource._cleanup` worktree removal followed by its private-root removal.
No copied tree, current working tree, alternate checkout, stale private root,
or working-tree fallback is equivalent. The dependency root is the existing
controller-private immutable projection of the authenticated dependency lock;
its complete file/distribution material must reconstruct the claimed existing
closed-environment identity. A path string alone never authorizes either root.

Python remains `-I -S`. After gate consumption, bootstrap order is exactly:
(1) authenticate and read FD 6; (2) parse the canonical envelope; (3)
reconstruct and compare its bootstrap identity and operation/generation/profile
bindings; (4) select the exact role in `BOUNDED_STREAMING_WORKER_DISPATCH`; (5)
authenticate the source manifest and every actual closure byte; (6) authenticate
the dependency absence/presence object, identity, manifest, and actual bytes;
(7) authenticate runtime-bundle manifest and actual bytes, temporarily install
only its authenticated stdlib/dynamic-library roots, reconstruct its closed
host/runtime metadata and identity, and compare them; (8) replace `sys.path`
for MODEL-A roles with authenticated `<source_root>/src` first, authenticated
dependency root second when present, then those exact ordered authenticated
runtime roots. For input projector, do not add `<source_root>/src`; retain only
the authenticated dependency/runtime roots and install the exact MODEL-B
shell/finder/loader session; (9) import only the mapped implementation module
and resolve only its exact `main` function; (10) import the authenticated project
canonical module and repeat parser, canonical-byte, and domain-identity parity
for the accepted bootstrap value; (11) parse and validate
`worker_request_canonical_json` with existing trusted authority and continue.
No root enters `sys.path` before its actual material passes its corresponding
request-bound manifest. Immediately after imports, the origin guard enumerates
every loaded repository-owned module, including `orev3`, selected tests,
initializers, conftests, and helpers, requires its resolved origin to equal
exactly one authenticated closure path, and rejects a mutable-working-tree, alternate-root,
same-name, initializer, or out-of-closure origin. Later project imports remain
under that guard. An import failure never expands the closure, adds a path, or
retries through ambient authority; it is a closed hard failure requiring new
governance. There is no
`PYTHONPATH`, user site, editable install, script/current-working-directory
entry, ambient site-packages, or fallback root.

Every worker/controller script is authenticated before launch from the
approved Source-S commit as its exact repository-relative path, safe regular
mode-100644 Git blob, Git object identity, byte count, SHA-256, and existing
worker-module/component or closed worker-code-closure identity. The resolved
private execution path must contain those exact authenticated bytes. Argv
spelling or `proc_pidpath` alone is never script authority.

Post-launch argv authentication uses Darwin `sysctl` with the exact MIB
`(CTL_KERN, KERN_PROCARGS2, pid)`. This primitive was exercised on the governed
Darwin 24.0.0/CPython 3.14.5 host and returned the live child's exact argv.
The frozen final Python worker argv has exactly five entries: the exact Python
executable, `-I`, `-S`, the exact shared bootstrap script, and
`--governed-fixed-fds-v1`. `runtime.py` first obtains the bounded required buffer size, rejects zero
or a value above `1048576`, reads once, interprets the first native Darwin
32-bit `argc`, skips the NUL-terminated executable path and NUL padding, then
extracts exactly `argc` NUL-terminated UTF-8 arguments; truncated, malformed,
extra-argument, query, permission, or decode failure rejects. Environment bytes
following those `argc` strings are not argv and cannot establish authority.
The wrapper's full vector is compared byte-for-string to the reconstructed
wrapper vector. After exec, the same process instance's vector is compared to
the exact Python suffix. Thus wrapper argv proves the intended
`sandbox-exec -p <profile>` transition while final `proc_pidpath` and final argv
prove the Python executable, script, and fixed control argument. Worker claims
or startup attestations are not substitutes for this independent query.

The only allowed executable transition is the already authenticated
`/usr/bin/sandbox-exec` to the exact authenticated Python interpreter in the
same `GovernedProcessInstanceV1`. The controller waits for that final
`proc_pidpath` and argv while the Python code is blocked on descriptor 3; any
intermediate or final executable other than those two rejects. Immediately
before emitting `0xa5`, the controller revalidates wrapper and worker process
instances, exact two-role group membership, final Python executable, both exact
argv vectors, script bytes/closure, request descriptor authority, and the
allowed inherited descriptor set. That set is exactly stdin `/dev/null`,
controller-captured stdout and stderr, descriptors 3 through 6 as classified
above, and no other open descriptor. Enumeration uses
`proc_pidinfo(PROC_PIDLISTFDS)` and type-specific `proc_pidfdinfo`; an unknown,
extra, missing, writable request/lease, wrong endpoint type, or substituted
descriptor rejects. Type-specific identities are the pipe handle plus read-end
role for FD 3, socket identity and connected endpoint role for FD 4, and
`(st_dev, st_ino)` plus exact access flags for FDs 5 and 6. Exactly one enumerated
FD may match each identity; a second gate, reservation, lease, or request alias,
including any alias above 6 retained by a wrapper, rejects. Only after this
complete check may the controller release the gate.

Each role is a `GovernedProcessInstanceV1`, captured using
`libproc.proc_pidinfo(PROC_PIDTBSDINFO)` as
`(pbi_pid, pbi_start_tvsec, pbi_start_tvusec)`. The governed-host query returned
the complete 136-byte structure and stable tuples. Each worker RSS sample uses
`PROC_PIDTASKINFO.proc_taskinfo.pti_resident_size` only after immediately
revalidating that tuple. PID alone never authorizes sampling or signaling.

Group membership is enumerated with
`libproc.proc_listpids(PROC_PGRP_ONLY, wrapper_pbi_pgid, ...)`. Before gate
release, normal membership is exactly the authenticated wrapper and worker.
During orderly completion, worker disappearance followed by wrapper exit is
valid. Immediately before signaling, membership is re-enumerated and every
extant member must match its captured role. Unexpected membership, missing
mandatory active worker, query failure, executable or start-time substitution,
or group substitution returns `RESOURCE_PROCESS_INSTANCE_MISMATCH` and sends
no signal.

Termination targets the invocation group only after that final role check.
`runtime.py` records the PID returned by `os.posix_spawn` as the sole
measurement-wrapper PID in one `GovernedSpawnHandle`; no second owner or reaper
is permitted. It immediately captures the wrapper process-instance identity
and leaves that PID unreaped until monitoring and any termination decision are
complete, anchoring the group leader PID, session, and process group. Worker
PID discovery never uses a child-process object: bounded
`proc_listpids(PROC_PGRP_ONLY, wrapper_pid, ...)` polling requires the captured
wrapper plus exactly one other PID, whose start identity, initial/final
executable transition, parent PID equal to wrapper PID, group, session, argv,
and FD set are then authenticated as the governed worker. Zero, multiple, or
substituted candidates reject without gate release.

Final reaping is exactly one `os.waitpid(wrapper_pid, 0)` call retried only on
`InterruptedError`; it occurs after clean completion or authenticated
termination and records the returned PID and raw status. A different PID,
`ChildProcessError`/`ECHILD`, or second reap is
`RESOURCE_PROCESS_INSTANCE_MISMATCH`. Status is decoded only with
`os.WIFEXITED`/`os.WEXITSTATUS` or `os.WIFSIGNALED`/`os.WTERMSIG`; stopped,
continued, malformed, or unknown status rejects. Failure cleanup performs this
same sole-reaper loop after safe termination, so no zombie or competing waiter
is permitted. An already-exited wrapper remains unreaped and authenticated
until this final call.

The worker cannot fork and an outside process cannot
join the wrapper's new session, so membership between check and `killpg` can
only shrink by expected exit. No descendant is signaled individually. If a
role exits, it is omitted only after verified exit; if membership is not closed,
no signal is sent. The spawned-wrapper unreaped rule protects only the wrapper PID
from reuse. Worker identity is protected while extant by start time and group;
after exit it is never sampled or individually signaled.

`runtime.py` samples the authenticated Python worker at the adopted interval
and may terminate sustained RSS above `watchdog_rss_bytes`; this remains defense
in depth. `/usr/bin/time -l` is acceptance evidence only and is not a watchdog
input. Its `maximum resident set size` is Darwin `wait4` resource usage for its
direct command child. Because sandbox-exec execs within that child, the value
measures the governed Python worker execution, including its exec transition,
not the persistent time wrapper. Descendants are forbidden and no descendant
aggregation is claimed.

Controller RSS uses the analogous outer topology without sandbox-exec: the
readiness supervisor launches `/usr/bin/time -l`, whose child execs the
authenticated controller and blocks on the start gate until captured. Worker
invocations occupy distinct new process groups below that controller. On
controller termination, any active worker invocation is authenticated and
terminated first, then the controller wrapper group is independently checked
and terminated.

### 11.1 Versioned generic policy and generation overlay

Legacy bytes remain immutable. In particular,
`config/research/readiness/evidence-preparation-policy-v1.json` and
`src/orev3/execution/schemas/v1/evidence-preparation-policy.schema.json` are
not modified. Every existing historical, prospective-v1.1, and
`ADAPTER_V4_CONFIGURATION_RESOURCE` generation continues to select that exact
policy and schema.

The bounded implementation prospectively creates exactly:

- policy identifier
  `experiment-evidence-preparation-policy-bounded-streaming-v1`;
- policy revision `"1"`;
- policy path
  `config/research/readiness/evidence-preparation-policy-bounded-streaming-v1.json`;
- schema registry identifier
  `evidence-preparation-policy-bounded-streaming-v1`;
- schema path
  `src/orev3/execution/schemas/v1/evidence-preparation-policy-bounded-streaming-v1.schema.json`;
- schema `$id`
  `orev3://schemas/execution-readiness/v1/evidence-preparation-policy-bounded-streaming-v1`;
  and
- schema title `EvidencePreparationPolicyBoundedStreamingV1`.

The new policy is closed. Its top-level fields are exactly `schema_version`,
`policy_identifier`, `policy_revision`, `policy_identity`,
`profile_renderer_identity`, `bounded_launch_authority`, `limits`, and
`worker_profiles`.
`schema_version` is integer `1` and `policy_revision` is string `"1"`.
`bounded_launch_authority` is a closed object containing exactly
`spawn_mechanism: "darwin-os-posix-spawn-file-actions-v1"`,
`cwd_policy: "cwd-ignored-absolute-fd-authority-v1"`,
`bootstrap_identifier: "bounded-streaming-worker-bootstrap-v1"`,
`bootstrap_path:
"src/orev3/execution/bounded_streaming_worker_bootstrap.py"`,
`bootstrap_request_identity_domain:
"orev3:bounded-streaming-worker-bootstrap-request:v1\n"`,
`bootstrap_request_max_bytes: 4194304`,
`measurement_wrapper_identifier:
"darwin-time-measurement-wrapper-v1"`, and
`measurement_wrapper_identity:
"09cc63835b888387783d32d0011fd0a0d344c3ba9620a947dfabd5bcfd521201"`.
These fields enter the existing policy identity and are independently compared
before every bounded launch and during current-readiness/Git reconstruction.

One new member is added identically to all three finite generation enums:
`ADAPTER_V4_EXPERIMENT5_BOUNDED_STREAMING`, serialized exactly as
`prospective-v1.1-adapter-v4-experiment5-bounded-streaming` in
`ProspectiveRegistryGeneration`, `PreparationAuthorityGeneration`, and
`EvidenceAuthorityGeneration`. No other generation selects the new policy.
Its Phase-3A schema overlay is byte-for-byte the adapter-v4 Phase-3A overlay.
Its Phase-3B and final overlays retain the adapter-v4 replacement of
`adapter-declaration` v3 by v4 and additionally replace only the
`evidence-preparation-policy` schema member by the bounded-streaming schema;
the governed member counts remain 10, 20, and 29.

The exact new constants are
`PROSPECTIVE_BOUNDED_STREAMING_PHASE3B_SCHEMA_POLICY`,
`PROSPECTIVE_BOUNDED_STREAMING_PHASE3B_SCHEMA_DOCUMENT_POLICY`,
`PROSPECTIVE_BOUNDED_STREAMING_READINESS_SCHEMA_POLICY`, and
`PROSPECTIVE_BOUNDED_STREAMING_READINESS_SCHEMA_DOCUMENT_POLICY`.
Policy selection is closed by `EVIDENCE_POLICY_PATH_BY_GENERATION` and
`EVIDENCE_POLICY_IDENTIFIER_BY_GENERATION`; each contains every supported
generation exactly once. The new generation maps only to the new path and
identifier; all prior keys map to the frozen v1 values. Requests, loaders,
sibling handoffs, current-readiness reconstruction, and Git reconstruction
must compare the same generation, policy path, identifier, revision, SHA-256,
Git object, schema identity, and policy identity.

There is no latest lookup, fallback, retry under another policy, simultaneous
same-kind schema membership, or ambient path. Unknown generation, absent map
entry, extra or aliased entry, generation-policy substitution, or schema or
document-map substitution rejects. The five Experiment/generic pairs above
must be equal. Generic RSS-acceptance, watchdog, disk, and timeout values have no
duplicate Experiment field; the Experiment configuration instead binds the
exact new policy identity. A mismatch is authority failure, not minimum-value
negotiation.

The Experiment-specific configuration at
`config/research/readiness/rq003-experiment-005-source-processing-v1.json`
adds exactly one top-level lowercase-64-hex field named
`bounded_evidence_preparation_policy_binding_identity`. Its schema authority
is the closed `_CONFIGURATION_FIELDS` and validation in
`src/orev3/experiments/rq003_experiment5_source_processing.py`, plus the
Experiment-005 configuration schema's `source_processing` resource binding.
The value is reconstructed by
`reconstruct_rq003_experiment5_bounded_policy_binding_identity` under domain
`orev3:rq003-experiment-005:bounded-evidence-preparation-policy-binding:v1\n`
from exactly:

```json
{
  "authority_generation": "prospective-v1.1-adapter-v4-experiment5-bounded-streaming",
  "evidence_preparation_policy_identifier": "experiment-evidence-preparation-policy-bounded-streaming-v1",
  "evidence_preparation_policy_identity": "<reconstructed policy_identity>",
  "evidence_preparation_policy_path": "config/research/readiness/evidence-preparation-policy-bounded-streaming-v1.json",
  "evidence_preparation_policy_revision": "1",
  "generic_limits": {
    "max_aggregate_collection_bytes": "<policy integer>",
    "max_collection_members": "<policy integer>",
    "max_file_bytes": "<policy integer>",
    "max_projection_bytes": "<policy integer>",
    "max_source_records": "<policy integer>"
  },
  "source_processing_configuration_identifier": "rq003-experiment-005-source-processing-v1",
  "source_processing_limits": {
    "maximum_aggregate_bytes": "<configuration integer>",
    "maximum_member_bytes": "<configuration integer>",
    "maximum_members": "<configuration integer>",
    "maximum_projection_bytes": "<configuration integer>",
    "maximum_records": "<configuration integer>"
  }
}
```

Angle-bracket strings above denote the named reconstructed scalar values, not
literal material. The function first reconstructs and authenticates policy
bytes, schema, Git object, SHA-256, and `policy_identity`; then it requires all
five paired integers to be equal; then it reconstructs the binding and compares
the claimed field. `validate_rq003_experiment5_bounded_streaming_policy_binding`
in `src/orev3/execution/evidence_preparation.py` is the single pre-Phase-3B
comparison authority and runs before snapshot or worker processing. The same
function is called on independently reloaded bytes during current-readiness and
Git reconstruction. Omission, substitution, legacy identity, generation
mismatch, paired-limit mismatch, or coordinated resealing rejects as
`PROFILE_POLICY_MISMATCH`. Because the claimed binding is inside canonical
source-processing configuration bytes, its change also changes the existing
configuration SHA/Git/decoder and Experiment-specific configuration bindings.

## 12. Prospective numeric-envelope adoption procedure

The numeric cycle is explicit: the first full-envelope run must measure final
projection, disk, RSS, and watchdog values, while final policy identity cannot
exist until those values are adopted. The sole bridge is
`BOUNDED_STREAMING_MEASUREMENT_CANDIDATE`. It is non-authoritative,
implementation-candidate-only, and measurement-only. It cannot satisfy a
readiness prerequisite, appear in a production descriptor or registry, become
Source S, authorize Experiment 005 execution, or be promoted automatically.

This is a closed sub-mode of generation
`ADAPTER_V4_EXPERIMENT5_BOUNDED_STREAMING`, not a second generation. The exact
serialized mode field in both bounded policy and Experiment source-processing
configuration is:

```text
numeric_envelope_mode: "BOUNDED_STREAMING_MEASUREMENT_CANDIDATE"
```

The existing frozen paths
`config/research/readiness/evidence-preparation-policy-bounded-streaming-v1.json`,
`src/orev3/execution/schemas/v1/evidence-preparation-policy-bounded-streaming-v1.schema.json`,
`config/research/readiness/rq003-experiment-005-source-processing-v1.json`, and
`src/orev3/execution/schemas/v1/rq003-experiment-005-configuration.schema.json`
own this representation. No new policy, schema, or configuration path exists.
The final numeric adoption replaces the mode value with exact literal
`BOUNDED_STREAMING_NUMERIC_ENVELOPE_ADOPTED`; no other string, alias, latest
lookup, fallback, retry, or ambient selection is accepted.

The exact deferred-field vector is lexically ordered and appears identically in
both policy and source-processing configuration:

```text
deferred_numeric_fields: [
  "max_controller_peak_rss_bytes",
  "max_projection_bytes",
  "max_temporary_disk_bytes",
  "max_worker_peak_rss_bytes",
  "watchdog_poll_interval_milliseconds",
  "watchdog_rss_bytes"
]
```

The only canonical pending representation is the closed object
`{"status":"measurement_pending"}`. In measurement mode it is the exact value
of `max_controller_peak_rss_bytes`, `max_worker_peak_rss_bytes`,
`watchdog_rss_bytes`, and `watchdog_poll_interval_milliseconds`. JSON null,
omission, empty object/string, alternate status, extension field, numeric
sentinel, maximum integer, infinity, host-capacity value, percentage, power of
two, or multiplier is invalid. Projection and disk need enforceable
measurement-run safety bounds and therefore remain finite integers while also
remaining in the deferred vector because those integers are not final adopted
operational ceilings.

The four source-derived limits remain fully authoritative and exactly enforced
in measurement mode:

```text
maximum_members = max_collection_members = 256
maximum_member_bytes = max_file_bytes = 227867665
maximum_aggregate_bytes = max_aggregate_collection_bytes = 1749809411
maximum_records = max_source_records = 1442676
```

The finite measurement-run projection ceiling is mechanically derived without
output evidence. A projection contains at most one record per structurally
scanned lifecycle record, therefore no more than `maximum_records` records.
Measurement mode additionally rejects any single canonical projection record
whose LF-inclusive byte count exceeds `maximum_member_bytes`. Consequently:

```text
MEASUREMENT_MAX_PROJECTION_BYTES
  = maximum_records * maximum_member_bytes
  = 1442676 * 227867665
  = 328739211471540
```

Both `maximum_projection_bytes` and `max_projection_bytes` equal exactly
`328739211471540`. Checked unsigned-64 multiplication is required before use.
This is a finite safety ceiling for the exact authenticated source, not an
estimate, headroom rule, final operational value, or permission to expand
membership. Exact source hashes and the structural projection schema continue
to constrain actual output. The later numeric adoption replaces both values
with the independently reviewed exact canonical projection byte count.

Measurement-mode logical disk admission is also mechanical. The ledger charges
the exact Section 9 simultaneous schedule: authenticated source snapshots, two
complete measurement-ceiling projection candidates, one maximum in-progress
source publication, and fixed bounded file payloads consisting only of the
4,194,304-byte bootstrap request plus existing 1,048,576-byte stdout and
1,048,576-byte stderr maxima. Lease and directories have zero logical file
length; reservation frames are socket bytes and are not disk charge. Thus:

```text
MEASUREMENT_FIXED_FILE_BYTES = 4194304 + 1048576 + 1048576 = 6291456
MEASUREMENT_MAX_TEMPORARY_DISK_BYTES
  = maximum_aggregate_bytes
    + 2 * MEASUREMENT_MAX_PROJECTION_BYTES
    + maximum_member_bytes
    + MEASUREMENT_FIXED_FILE_BYTES
  = 1749809411 + 2 * 328739211471540 + 227867665 + 6291456
  = 657480406911612
```

`max_temporary_disk_bytes` equals exactly `657480406911612` in measurement
mode, with checked unsigned-64 arithmetic. This logical ceiling neither
preallocates space nor claims physical capacity. Every write still requires a
reservation, filesystem exhaustion remains a closed failure, and the measured
peak logical charge—not this safety maximum—supplies the proposed final disk
ceiling. No other operation-created regular-file category is permitted; adding
one requires governance rather than an unexplained reserve.

Memory safety remains the structural allocation contract in Section 10. Peak
RSS is evidence only. Because the authenticated source, parser dimensions,
retained-state shapes, process count, and output/disk growth are already finite,
measurement mode runs without an RSS acceptance threshold. The watchdog is
also inactive in measurement mode: both its threshold and cadence are pending,
and selecting either before observing governed behavior would recreate the
cycle. This does not claim watchdog protection or final RSS acceptance. The
candidate records that watchdog status is exactly
`measurement_pending_not_active`; final adoption must provide finite threshold
and cadence and the final-byte rerun must exercise them. Structural violation,
unexpected materialization, allocation overflow, OS allocation failure, or
filesystem exhaustion still rejects atomically.

Five-limit equality remains exact. The four source pairs equal the frozen
integers above and the projection pair equals the measurement ceiling above.
The deferred vector and mode must also be byte-identical across the two
objects. No marker/integer negotiation, minimum, override, or mixed mode is
permitted.

The measurement policy retains identifier
`experiment-evidence-preparation-policy-bounded-streaming-v1`, revision `1`,
and its already frozen path, but its identity material additionally binds
`authority_generation`, `numeric_envelope_mode`, the exact deferred vector,
all known source integers, both measurement-run safety integers, all four
pending objects, worker profiles, wrapper/runtime authority, and every other
closed policy field. Domain remains
`orev3:readiness-evidence-preparation-policy:v1\n`. The mode and pending objects
make its identity cryptographically distinct from the later final policy.

`bounded_evidence_preparation_policy_binding_identity` is reconstructed in
measurement mode over the same frozen domain and material from Section 11.1,
with the exact mode, deferred vector, policy identity, five paired limits, and
source-processing configuration identity included. Phase-3B accepts this
binding only through an explicit measurement-candidate entry point. Final
readiness candidate, current-readiness, final Git reconstruction, production
descriptor, and registry authority reject either measurement mode, its policy
identity, its binding, or any resource derived from it. Coordinated mode,
policy, configuration, identity, or binding resealing cannot establish final
authority.

The governed measurement output contains exact implementation-candidate path
hashes; exact 21-member manifest/input identities and source counts; projection
byte count, SHA-256, ordered record identities, lifecycle hashes, and all
dataset/content/projection identities; peak logical disk charge and schedule;
five cold-run controller and per-worker RSS byte values; exact host, runtime,
measurement-wrapper, sandbox, command, and policy identities; watchdog status
`measurement_pending_not_active`; timeout observations; and sequential two-run
byte/identity equality. Cold-run and `/usr/bin/time -l` parsing rules remain
exactly those already frozen. No warm run substitutes.

After independent evidence review, a separately authorized numeric adoption
must replace the mode, remove the deferred vector, replace all four pending
objects and both measurement bounds with final finite adopted integers, and
regenerate and rereview policy bytes/SHA/Git object/schema/identity;
source-processing bytes/SHA/Git object/configuration identity; bounded-policy
binding identity; schema constants; component, resource, Experiment-specific,
profiled-configuration and readiness identities; and every affected test byte.
There is no same-identity promotion and no automatic mutation. Measurement-mode
material remains rejected by final readiness after adoption.

The corrected acyclic sequence is:

```text
governance clarification freeze
  -> independently verified remote-backed clarification commit
  -> non-authoritative bounded-streaming implementation candidate using measurement mode
  -> governed full-envelope measurement evidence
  -> independent review of measurement evidence
  -> bounded numeric-envelope adoption
  -> dependent identity regeneration
  -> post-adoption exact-byte full-envelope rerun
  -> independent implementation review/freeze
```

This is a narrow value-measurement bridge, not permission to change the
architecture, source graph, scientific result, identity domains, or downstream
authority.

## 13. Outcome isolation

Complete-byte authentication remains mandatory. The selective semantic
whitelist remains closed. No parse-then-discard outcome path, raw outcome
retention, prohibited field-name diagnostic, raw excerpt, outcome locator,
opener, provider, or evaluation capability is introduced. Compact indexes
contain only offsets, coordinates, shape facts, and identities required for
deterministic reconstruction. The projection continues to contain only the
already-authorized scientific and opaque provenance material.

## 14. Scientific parity

Implementation must preserve exactly:

- the 21 members, member order, manifest identity, lifecycle and observation
  populations, and immutable source coordinates;
- schema revisions and source normalization rules;
- `end_slot - 5` selection and equal-RPC ordering;
- candidate order `0..24`;
- measurement definitions and vectors;
- repeated-observation and nonselection semantics;
- projection record/schema shape and identity domains;
- ranking, folds, controls, metrics, bootstrap, dispositions, and confirmation
  semantics.

An optimization that changes any of these is rejected and requires separate
prospective scientific governance.

## 15. Prospective implementation surface

The exact prospective surface is 38 paths: 26 production/configuration paths
and 12 test paths. Every listed path is REQUIRED; no MAYBE path exists. The
table authorizes no edit.

| Path | Disposition | Reason |
| --- | --- | --- |
| `config/research/readiness/rq003-experiment-005-source-processing-v1.json` | REQUIRED | Bind adopted source and record limits plus the exact measurement mode, deferred vector, projection safety bound, policy binding, and later regenerated final identities. |
| `config/research/readiness/evidence-preparation-policy-bounded-streaming-v1.json` | REQUIRED | New closed generic policy, exact measurement/final mode representation, bounded launch/cwd/bootstrap authority, and separate measurement-wrapper identity; legacy v1 remains byte-identical. |
| `src/orev3/execution/schemas/v1/evidence-preparation-policy-bounded-streaming-v1.schema.json` | REQUIRED | New closed policy schema, measurement-pending object and mode constraints, and final memory/disk/source-record fields. |
| `src/orev3/execution/readiness_record.py` | REQUIRED | Define bounded Phase-3B/final schema and document overlays without changing readiness-record schemas. |
| `src/orev3/execution/registry.py` | REQUIRED | Authenticate the new same-kind schema overlay and preserve finite registry counts. |
| `src/orev3/execution/readiness_contracts.py` | REQUIRED | Add the exact final generation and policy-map reconstruction. |
| `src/orev3/execution/preparation.py` | REQUIRED | Add the exact Phase-3A generation and bind its adapter-v4 overlay. |
| `src/orev3/execution/evidence_preparation.py` | REQUIRED | Add the exact Phase-3B generation, select the policy, and perform streaming comparison/publication. |
| `src/orev3/execution/evidence_preparation_worker.py` | REQUIRED | Provide the stdlib-only fixed-FD controller bootstrap, install authenticated import roots only after gate/request authentication, preserve generation across sibling handoff, and propagate exact limits. |
| `src/orev3/execution/preparation_worker.py` | REQUIRED | Move Phase-3A worker startup to the same stdlib-only fixed-FD bootstrap and defer network/project/runtime validation imports until gate, request, and root authentication complete. |
| `src/orev3/execution/detached_evidence.py` | REQUIRED | Bind detached request/loader generation equality. |
| `src/orev3/execution/readiness_candidate.py` | REQUIRED | Reconstruct the bounded generation and exact selected policy. |
| `src/orev3/execution/current_readiness.py` | REQUIRED | Independently reload the exact generation and selected policy. |
| `src/orev3/execution/git_state.py` | REQUIRED | Reconstruct the same schema/document/policy bindings from the approved commit. |
| `src/orev3/execution/test_policy.py` | REQUIRED | Carry the selected generic policy identity into exact readiness-test authority. |
| `src/orev3/execution/schemas/v1/rq003-experiment-005-configuration.schema.json` | REQUIRED | Update the frozen source-processing resource byte/SHA constants and constrain exact measurement/final mode material mechanically; no scientific field changes. |
| `src/orev3/execution/external_inputs.py` | REQUIRED | Stream immutable snapshot creation and aggregate admission. |
| `src/orev3/execution/filesystem_capability.py` | REQUIRED | Provide bounded streaming content-addressed publication with stable-descriptor and atomicity checks. |
| `src/orev3/execution/runtime.py` | REQUIRED | Reconstruct launch, cwd, detached-worktree, separate measurement-wrapper authority, and exact `construct_bounded_streaming_runtime_bundle_material` parity with existing `reconstruct_runtime_bundle_identity`; own `os.pipe`, scratch normalization, atomic `os.posix_spawn` file actions, fixed descriptors, positional FD-6 authentication, process/FD/argv checks, sole PID ownership/waitpid, dedicated status-70 integrity mapping and external cleanup, RSS/watchdog, reservation IPC, recovery, and Seatbelt confinement. |
| `src/orev3/execution/bounded_streaming_worker_bootstrap.py` | REQUIRED | New single stdlib-only gate consumer, closed bootstrap-envelope parser/identity verifier, source/dependency/runtime manifest verifier, exact input-projector `BoundedProjectImportSession`/finder/loader with complete CPython frame census, five-attribute thread-start denial, mutation-state tracking, non-returning status-70 terminal path, meta-path, project-cache, and restoration integrity, MODEL-A import handling for other roles, authenticated import-root installer, and exact five-entry worker dispatcher. |
| `src/orev3/execution/input_projection_worker.py` | REQUIRED | Provide the stdlib-only fixed-FD bootstrap, install authenticated import roots only after gate/request authentication, and drive authenticated structural passes and incremental projection output. |
| `src/orev3/execution/readiness_test_worker.py` | REQUIRED | Provide the stdlib-only fixed-FD bootstrap, authenticate the closed test/dependency roots after the gate, and import pytest only from the authenticated dependency root. |
| `src/orev3/execution/dataset_validation.py` | REQUIRED | Construct dataset/projection evidence from authenticated streaming summaries rather than full payloads. |
| `src/orev3/execution/replay_preparation.py` | REQUIRED | Reconstruct Replay incrementally from canonical JSONL. |
| `src/orev3/execution/replay_preparation_worker.py` | REQUIRED | Provide the stdlib-only fixed-FD bootstrap, install authenticated import roots only after gate/request authentication, and consume projection through the bounded Replay interface. |
| `src/orev3/experiments/rq003_experiment5_source_processing.py` | REQUIRED | Implement compact indexing, per-round reconstruction, streaming projection, and summary identities. |
| `tests/experiments/test_rq003_experiment5_source_processing.py` | REQUIRED | Exact envelope, scientific parity, limit, indexing, and late-failure tests. |
| `tests/execution/test_phase3b_external_inputs.py` | REQUIRED | Snapshot streaming, mutation, exact-bound, atomicity, and cleanup tests. |
| `tests/execution/test_phase3b_reconstruction.py` | REQUIRED | Two-run streaming byte/identity comparison and substitution tests. |
| `tests/execution/test_phase3b_integration.py` | REQUIRED | Governed sandbox end-to-end exact-envelope and failure evidence. |
| `tests/execution/test_phase3b_authority.py` | REQUIRED | Closed policy fields, cross-layer equality, worker propagation, and identity substitution tests. |
| `tests/execution/test_phase3c_schema_registry.py` | REQUIRED | Revised policy-schema authentication and unchanged governed registry membership/count tests. |
| `tests/execution/test_phase3c_readiness_record_v2.py` | REQUIRED | Policy reconstruction parity and proof that no readiness-record field or lifecycle state changes. |
| `tests/experiments/test_rq003_experiment5_configuration.py` | REQUIRED | Mechanical source-processing byte/SHA binding and scientific-configuration parity. |
| `tests/execution/test_phase3b_worker_boundaries.py` | REQUIRED | Local-bootstrap/project-canonical parity, four MODEL-A closures, exact 36-member input-projector MODEL-B shells/finder/loader/cache/origin enforcement, complete census/thread-hook/meta-path/session integrity, hook-install positions 1 through 5, installation-window, post-mutation terminal-exit, final-result race, ordinary restoration, and manifest sizing; readiness-test manifest and plugin suppression; runtime-bundle material/identity parity; FD-6 offset safety; atomic spawn/collision/concurrency; detached-source/import/cwd authority; measurement-wrapper identity; PID wait/reap; RSS/watchdog; reservation IPC; crash cleanup; and Seatbelt evidence. |
| `tests/execution/test_phase3a_preparation.py` | REQUIRED | Exact bounded generation and adapter-v4 Phase-3A overlay selection. |
| `tests/execution/test_phase3c_readiness_candidate.py` | REQUIRED | Candidate generation/policy reconstruction and substitution rejection. |
| `tests/execution/test_phase3c_current_readiness.py` | REQUIRED | Independent bounded-generation and policy reauthentication. |

Explicitly NOT REQUIRED and immutable are
`config/research/readiness/evidence-preparation-policy-v1.json` and
`src/orev3/execution/schemas/v1/evidence-preparation-policy.schema.json`.
No other production or test path is prospectively included. If another
trust-bearing path proves necessary, work stops for a bounded governance
amendment; a writer cannot add it discretionarily.

## 16. Required future acceptance

Before implementation freeze, evidence must prove:

1. the exact 21-member graph succeeds and its manifest identity remains
   `0387a21b4921428c932851c29bd790c5f70a7a3687d48df99614c6717f6d3658`;
2. every source byte count, SHA-256, logical identifier, member identity, and
   aggregate count remains exact;
3. exact source member/aggregate/record limits pass and one-over values reject;
4. projection cumulative exact-bound passes and the next byte is rejected
   before append;
5. measured peak memory and disk remain within the separately adopted finite
   ceilings;
6. no normal path uses complete-member `read_bytes`, complete split-line or
   parsed populations, complete projection payload materialization, or
   complete parsed Replay materialization;
7. late malformed input, duplicate key, truncation, mutation, second-pass
   mismatch, resource exhaustion, crash, and late projection failure yield no
   trusted output and leave only cleanable non-authoritative temporaries;
8. exact coordinate, ordering, repeated-observation, duplicate, conflict,
   selection, and nonselection behavior matches frozen authority;
9. no C2 or August 12-and-later raw member enters;
10. outcome-isolation sentinels prove no prohibited semantic read, retention,
    diagnostic, output, or capability;
11. two runs produce byte-identical projection streams and identical ordered
    record, dataset, content, projection, and Replay identities;
12. streaming Replay has exact parity with frozen synthetic scientific cases;
13. interruption at every publication phase leaves no authoritative partial
    result; and
14. cleanup removes incomplete private output without deleting authenticated
    content-addressed authority.

Memory evidence before numeric adoption proves the structural retained-state
contract, checked index arithmetic, controller/worker coverage, descendant
prohibition, no trusted partial result, and explicit characterization that a
short spike is not hard-quota contained. After numeric adoption the exact-byte
rerun additionally proves sustained watchdog termination with
`RESOURCE_MEMORY_EXCEEDED`. The evidence covers exact-bound and one-over record
bytes, decoded string and
key bytes, canonical non-string scalar bytes, nesting depth, object members,
array items, lifecycle references, offset arithmetic, and count
multiplication/addition overflow, rejecting before oversized construction.
Five cold full-envelope governed-host runs record controller and each worker
RSS through the exact parser in Section 12. The candidate is measured before
numeric adoption and the final adopted bytes are rerun afterward.

Static and dynamic evidence scoped to governed large source/projection data
rejects `Path.read_bytes()`, input-sized whole-file `.read()`, full-member
`splitlines()`, complete-payload `json.loads()`, joining complete projection
bytes, simultaneous duplicate reconstruction payloads, and complete Replay
materialization. Small fixed metadata/configuration reads remain permitted.
The malformed unreferenced July 23 line remains inert and absent from
diagnostics and science; an otherwise identical graph referencing that line
rejects.

Disk evidence directly covers a pre-existing deduplicated snapshot, a newly
created snapshot, concurrent operations sharing one snapshot, controller
private bytes, child-worker output, the sequential reconstruction-one/two
schedule, already-published projection reuse, hard-link accounting, exact-bound
success, and one-byte-over rejection before write or publication. It forces a
growth attempt between accounting observations and proves reservation prevents
the race. It also proves failure cleanup, crash/orphan recovery, atomic rename,
and concurrent-operation attribution without deleting authenticated shared
objects. Direct negatives cover growth without reservation, missing or forged
acknowledgment, substituted operation ID or sequence, worker crash after
growth, controller crash after reservation, stale operation root, live-versus-
orphan classification, lock-holder death, restart reconciliation, crash during
link/publication and cleanup, concurrent deduplication, exact-bound success,
and one-byte-over rejection before growth.

The governed-host positive topology test uses the real `/usr/bin/time -l` to
`sandbox-exec` to authenticated Python-worker command. It proves the persistent
wrapper, same-instance sandbox exec transition, two-member active group,
start-gate authentication, intended worker RSS target, clean
completion, and absence of false `RESOURCE_PROCESS_INSTANCE_MISMATCH`.
Measurement-mode topology evidence records the authenticated RSS target but
marks watchdog sampling inactive; the watchdog sample and termination clauses
apply to the mandatory post-adoption rerun.
Negatives cover unexpected group member, missing wrapper or worker, wrapper or
worker executable substitution, legitimate versus substituted exec transition,
PID and descendant-PID reuse, start-time mismatch, query/permission failure,
worker exit between sample and recheck, membership change before termination,
unexpected descendant spawn, group substitution, and termination-target
mismatch. Every case proves zero signals to an unrelated process and that
unreaped retention protects only the direct wrapper PID.

The same production-shaped positive test proves `os.pipe()` exists, both new
endpoints are non-inheritable and `FD_CLOEXEC`, scratch normalization and
atomic `os.posix_spawn` file actions install only the read endpoint at fixed
descriptor 3, and descriptors 3 through 6 survive `/usr/bin/time` and
`sandbox-exec`. It observes the Python worker blocked before descriptor 6 is
read and proves the parent never mutates destinations 3 through 6. It
independently authenticates both process instances and group,
`proc_pidpath`, exact wrapper and post-exec worker argv through
`KERN_PROCARGS2`, bootstrap and selected-entrypoint Source-S bytes/closures, request descriptor and
identity, and the exact inherited descriptor set. It then writes only `0xa5`,
closes the controller endpoint, observes single consumption and permanent gate
closure, and proves request parsing begins only afterward and normal execution
continues.

Start-gate and mapping evidence covers missing or wrong descriptor 3, wrong
initial or final CLOEXEC/inheritability, deliberate child inheritance, missing
gate after either exec, absent controller write-end in the worker, premature
controller close, zero bytes, EOF before release, wrong byte, two/trailing
bytes, replay, second read, reused descriptor, and duplicate gate alias. The
fixed-mapping matrix covers every source already at target, each single target
collision, cycles 3/4, 4/5, and 3/4/5/6, unrelated parent occupants at each
destination, mixed open/closed destinations, stdout/stderr allocation
collisions, scratch allocation within 3 through 6, duplicate source, every
file-action construction/spawn failure, scratch/source leak, and exact proof
that parent destination state never changed. It also rejects second aliases of
each gate, reservation, lease, or request open-file description, including
aliases above 6 or retained unexpectedly through a wrapper.

A concurrency test holds one governed launch after scratch creation while
another thread performs the existing `git_state.py` bounded-process launch and
a second governed spawn. It
proves all originals/scratches remain CLOEXEC, file actions are per-child,
neither launch inherits the other's descriptors, parent FDs 0 through 6 never
change, and no common lock is needed. Mutated `os.posix_spawn`, file-action
order/constants, scratch allocator, CLOEXEC assertion, or `setsid` authority
rejects. No test may introduce `preexec_fn` or parent-global remapping.

Bootstrap/import tests prove isolated Python reaches and consumes the gate with
only the exact stdlib bootstrap, FD 6 is unread before release, authenticated
request and roots reconstruct afterward, `sys.path` has the exact source,
dependency, and runtime-bundle order, and governed project modules then import.
Negatives cover request parsing, project import, or root installation before
the gate; `PYTHONPATH`, user-site, editable-install, current-directory shadow,
ambient site-packages, alternate or unauthenticated source/dependency root,
same-name modules under a wrong root, root ownership/mode/symlink/byte/identity
substitution, and request/closure/runtime-bundle substitution. Every failure is
closed, releases no governed input, and produces no trusted partial result.

Source-root tests additionally reject a wrong absolute root; correct claimed
identity with changed member bytes; same filenames with changed bytes; missing,
duplicate, reordered, extra-manifest, symlink, nonregular, or wrong-mode closure
members; path traversal, non-NFC, and path escape; wrong Git object/count/SHA;
and coordinated root-path, manifest-identity, closure-identity, and member
resealing when actual frozen bytes differ. Dependency tests cover the exact
`{"present":false}` positive and the exact present positive, and reject null,
omission, empty-string absence, false plus extra fields, true with missing
fields, presence substitution by role, wrong root/package bytes, missing or
extra materialized member, same-name module from another location, manifest or
claimed-environment resealing, and claimed identity without actual byte parity.
Runtime-root tests reject a wrong stdlib root, wrong dynamic-library root,
unmanifested or ambient root, host/runtime substitution, wrong executable or
file material under the same claimed runtime identity, symlink escape, and
coordinated path/identity/material resealing.

For each of the five dispatch rows, one positive proves that its exact
identifier selects its exact request kind, module, `main`, closure identifier,
and new ordered import-complete closure tuple. Each positive authenticates the
complete manifest, installs only authenticated roots, imports the mapped module,
resolves the exact callable, exercises representative startup, and records zero
out-of-closure project imports. Direct negatives substitute another
governed role, an unknown or alias identifier, wrong request kind, module,
callable, closure identifier, or closure tuple, and coordinate identifier/map/
module/callable/closure substitutions. Every such case rejects before project
import and invokes no substituted callable.

Import-closure negatives remove each legitimately imported member in turn,
add an unauthorized project module, mutate module or package-initializer bytes,
place a same-name module outside the closure, attempt a relative import escape,
trigger a transitive or runtime-discovered project import outside the manifest,
reorder identity-bearing members, and coordinate manifest/identity resealing.
Post-import origin verification rejects every case without fallback.
Readiness-test-specific negatives select a test outside the six-file manifest,
an alternate conftest or helper, arbitrary pytest plugin, environment-loaded
plugin, substituted node ID/path, and a same-name test under another root.

`tests/execution/test_phase3b_worker_boundaries.py` owns the input-projector
MODEL-B evidence. Its positive authenticates the exact 36-member manifest,
constructs exactly eight shells, installs the exact finder/loader, reaches
representative source-processing startup, records every loaded `orev3` name,
and proves each source module belongs to the map while no real initializer or
initializer-only module executes. Each shell is checked for exact `__name__`,
`__package__`, one-element `__path__`, null loader, package `ModuleSpec`, exact
search locations, and absence of forwarding or side effects.

Direct negatives cover `orev3.features.pipeline`,
`orev3.strategy_lab.settlement`, `orev3.strategy_lab.transactions`, every other
out-of-closure project module, same-name source elsewhere, working-tree source,
forged cached authorized and cached unauthorized modules, real initializer
execution, relative escape, later-finder fallback, and runtime closure
expansion. Execution sentinels prove rejected source never executes. Cache tests
preload an unrelated `orev3` module, a forged mapped module, and a package
object; success and every failure stage must restore exact object references,
remove originally absent keys, and leave no session finder, loader, shell, or
module. The same test reconstructs the 36-member count, 9,571-byte current-HEAD
manifest, feasibility identity, and complete-envelope estimate. Governed
end-to-end behavior remains in `test_phase3b_integration.py`; scientific
streaming behavior remains in
`tests/experiments/test_rq003_experiment5_source_processing.py`.

That owner also proves the Model-B session-exclusivity authority directly. A
positive requires `sys._current_frames()` to contain exactly the identifier
from `threading.get_ident()`, records the exact pre-session `sys.meta_path`
sequence and `orev3`-domain cache, installs and identity-checks all five denial
attributes, repeats the complete census before global import mutation, performs
representative startup, observes the singular census and exact governed
meta-path/hook shape at every checkpoint, and restores all globals and original
callables exactly afterward.

Governed-host census probes cover ordinary `threading.Thread`, raw
`_thread.start_new_thread`, and `_thread.start_joinable_thread` with an explicit
`_thread._ThreadHandle`. For the two raw forms, the live worker identifier must
appear in `sys._current_frames()` while remaining absent from
`threading.enumerate()`. A preexisting raw worker therefore makes the census
cardinality greater than one and rejects before hook installation or any
`sys.modules`/`sys.meta_path` mutation through exact status 70. Malformed census
material, missing current identity, and census exceptions use the same uniform
pre-mutation terminal path.

Every frozen start attribute is tested directly:
`threading.Thread.start`, `threading._start_joinable_thread`,
`_thread.start_new_thread`, `_thread.start_new`, and
`_thread.start_joinable_thread`. Representative `threading.Timer.start` and
`ThreadPoolExecutor` worker creation are also attempted. Every attempt raises
the closed integrity failure, returns no handle, and leaves the complete census
singular. Alias tests prove the two joinable attributes are both patched even
when initially identical and prove the two distinct `start_new` attributes are
independently patched.

Partial-installation acceptance is an exact four-row matrix over installation
positions 2, 3, 4, and 5 in that frozen attribute order. For each position
`N`, deterministic test-only fault injection permits hooks 1 through `N - 1`
to be replaced successfully by their exact denial objects, then makes
replacement of hook `N` fail before that attribute changes. The first
successful replacement has already transitioned the worker to
`GLOBAL_INTERPRETER_STATE_MUTATED`; therefore every row must invoke
`os._exit(70)` immediately. The test technique used to make assignment fail is
not production authority.

Each of those four rows proves that no restoration helper for the previously
replaced hooks runs; no `sys.modules` or `sys.meta_path` mutation occurs; no
synthetic shell or bounded finder is installed; no ordinary project, semantic,
or session cleanup sentinel runs; no `finally` or `atexit` sentinel runs; and
no trusted result or worker diagnostic is constructed or transmitted. Through
the already-governed Python-worker -> sandbox-exec exec lineage ->
`/usr/bin/time` transport, the controller observes status 70, maps it to
`BOUNDED_PROJECT_IMPORT_SESSION_INTEGRITY`, performs the existing external
process/descriptor/reservation/disk/operation-root cleanup, and publishes no
partial output.

A contrasting hook-1 test injects failure before the first replacement
completes. Provided no other governed global mutation occurred, the state
remains `PRE_MUTATION`; no hook has changed, no import global has changed, and
the existing uniform pre-mutation `os._exit(70)` rule applies. It is not
classified as post-mutation merely because replacement was attempted. If any
other governed mutation had already succeeded, the state is instead
`GLOBAL_INTERPRETER_STATE_MUTATED` under the unchanged first-mutation rule.

An installation-window race attempts creation between the first census and
completion of denial installation. If creation wins, the immediately repeated
census observes the worker; otherwise the denial prevents it. In both outcomes
no project/global import state changes and no session starts with more than one
Python-executing thread. Further negatives introduce a thread during setup,
governed import, semantic processing, and immediately before cleanup, and
replace, delete, prematurely restore, or cross-substitute each denial
attribute. Every case produces
`BOUNDED_PROJECT_IMPORT_SESSION_INTEGRITY` and trusts no result. A hook failure
uses status 70; an observed extra thread or census failure after mutation uses
status 70 without executing Python cleanup. Synchronization barriers and events
used to make these races deterministic are test machinery only and establish
no production authority.

Dedicated subprocess negatives enter the Model-B session, perform the first
global mutation, introduce a controlled second Python thread, and prove the
next census calls `os._exit(70)` without executing `finally`, `atexit`, cache,
meta-path, finder, shell, or hook-restoration sentinels. The controller must
observe propagated wrapper status 70, map it to the closed integrity failure,
accept no result, and complete descriptor, reservation, operation-root, and
partial-output cleanup externally. A separately injected post-mutation census
exception or malformed census has the identical result. A combined hook bypass
and live second thread also terminates rather than restoring in process.

A contrasting ordinary import or semantic failure keeps the complete census
singular and all hooks intact, and must restore finder, cache, meta path, and
hooks exactly in process. Another race introduces the second thread immediately
before result transmission: the final census must prevent construction or
transmission of trusted success and terminate with status 70. EOF, truncated
worker protocol, or buffered candidate bytes must not override that decoded
status.

Meta-path negatives insert an extra finder, remove or reorder a preexisting
finder, replace a preexisting finder, and remove or replace the bounded finder.
Project-cache negatives insert an unauthorized `orev3` key, replace a loaded
mapped module, replace or delete a synthetic shell, and insert a forged object
under an authorized but not-yet-loaded name. Cleanup negatives inject project
import failure, semantic-processing failure, census/hook mismatch, meta-path
mismatch, and project-cache mismatch at cleanup. Each proves no trusted output;
where the recorded objects remain recoverable, it also proves exact reference-
identity restoration, original absence restoration, and removal of every
session finder, loader, shell, and module. An unrecoverable restoration mismatch
is a complete worker/controller failure rather than permission to continue in
the contaminated interpreter.

Direct bootstrap-parser tests cover one exact canonical envelope; duplicate
keys; malformed UTF-8; whitespace and key-order changes; missing and extra
outer/nested fields; booleans in integer positions; signed/unsigned boundary
and one-over values; JSON null at every nesting position; the exact dependency
absence object; every float; `NaN`, `Infinity`, and `-Infinity`; non-NFC and
lone-surrogate strings; nested
closed arrays/objects; empty, LF-, CRLF-, BOM-, truncated-, and trailing-framed
input; exact 4,194,304-byte bootstrap acceptance and 4,194,305-byte bootstrap
rejection; request identity mismatch; payload size/SHA mismatch; mutation of
every top-level authority field; entrypoint-map or parser-function substitution;
and complete parity with the trusted readiness parser using explicit
`max_bytes=4194305` after the sole appended LF. Controller and worker must
produce identical canonical bytes and bootstrap identity. The identity field is
excluded exactly once; resealing it cannot authorize mismatched root, closure,
runtime, request, operation, generation, or profile material. A mismatch stops
freeze.

Local-canonical tests directly compare `bootstrap_parse_request_bytes`,
`bootstrap_canonical_bytes`, and `bootstrap_domain_identity` with authenticated
project `parse_canonical_bytes`, `canonical_bytes`, and `domain_identity` only
after root installation. A sentinel makes any pre-root `orev3` import fail and
proves local identity reconstruction succeeds without it. Local-function
substitution, altered escaping, missing material LF, alternate integer spelling,
or SHA algorithm substitution is a hard failure.

FD-6 tests prove controller chunked `pread` leaves the shared offset at zero,
the worker observes zero and reads exactly once to EOF, post-read stability
passes, and FD closes. Negatives deliberately replace controller `pread` with
ordinary read and detect EOF offset, set every nonzero initial offset, trigger
short/truncated/extra data and metadata/content mutation between controller
authentication and worker read, attempt a pre-gate worker read, and attempt a
path reopen. No test may repair an unexpected offset by seeking.

Detached-source tests exercise only `DetachedSource` creation and cleanup and
reject current-working-tree substitution, an alternate copied tree, symlink,
wrong/stale commit, wrong tree or blob, wrong root ownership/mode, changed
governed path, and stale private worktree.

Measurement-wrapper tests reconstruct the exact separate authority and accept
the frozen `/usr/bin/time` bytes. They reject another absolute path, symlink,
replacement bytes, mode/owner/size/SHA mismatch, host-system/architecture/
Darwin mismatch, policy identity substitution, and coordinated claimed-
identity resealing. They also prove legacy runtime-contract executable
membership stays byte-identical and does not claim `/usr/bin/time`.

Cwd tests run the bounded launch from multiple wrong/arbitrary inherited cwd
values and prove identical absolute/FD authority. They reject every relative
executable, script, request, source, dependency, profile, and output path,
worker `getcwd` authority, cwd-derived `sys.path`, and cwd shadow module, while
proving all legacy generations retain `detached_source_root` behavior.

Spawn ownership tests prove the returned PID is the authenticated time wrapper,
worker discovery uses the exact group query rather than a child-object PID,
`waitpid` retries EINTR, decodes clean and signaled status, reaps exactly once,
and rejects wrong returned PID, ECHILD, competing/double reaper, malformed
status, and zombie leakage.

Process-start substitution tests cover the correct Python interpreter with the
wrong script, the authenticated script with the wrong interpreter, time-wrapper
substitution, sandbox executable/profile/argument substitution, request
descriptor substitution, operation/generation/profile-binding substitution,
extra, missing, or reordered argv, environment-derived path substitution,
wrapper or worker `KERN_PROCARGS2` query/parse failure, and an illegitimate exec
target. A separate positive proves the exact same-instance
`sandbox-exec -> Python` transition is accepted. Script tests mutate path,
mode, Git object, bytes, SHA-256, and closure identity independently. No case
may rely on `proc_pidpath` alone or on a worker-reported attestation.

Operation-ID evidence patches only the CSPRNG boundary and proves one exact
16-byte request to `secrets.token_hex`, lowercase 32-hex encoding, prefix,
wrong length/case rejection, caller/deterministic/substituted generator
rejection, exclusive-root races, collision retries, the 128-collision hard
stop without call 129, and canonical CSPRNG failure.

Wire evidence covers short prefix, wrong endianness, zero, 294, 295, truncated
payload, concatenated/trailing frame, and every EOF state. Canonical-payload
tests cover whitespace, key order/re-encoding, duplicate, extra/missing field,
wrong type, float/nonfinite/overflow numeric material, operation mismatch,
sequence replay/skip/order, category substitution, negative/overflow growth,
wrong acknowledgment identity/sequence/growth, acknowledgment or rejection
substitution, and extra fields. Behavioral tests prove no pre-ack write, no
write beyond allowance, conservative death-after-ack charge, controller death
during request, and unchanged ledger after malformed or replayed messages.
Regression tests explicitly reject the obsolete path-bearing request, a
`reserved` response, an authorized-new-size response, a one-code-only legacy
rejection shape, and every alias for the current field names.

Policy evidence proves every legacy generation selects the exact legacy path,
identifier, schema, and bytes, while only
`ADAPTER_V4_EXPERIMENT5_BOUNDED_STREAMING` selects the new policy. Direct
mutations of policy identifier, revision, path, SHA-256, Git object, schema
identity, policy identity, generation-to-policy map, and schema/document maps
reject. Cross-generation substitution, Experiment/generic paired-limit
inequality, a legacy request consuming new fields, a bounded request falling
back to v1, unknown generation, retry, and ambient/latest selection all reject.
It also rejects omitted, substituted, or legacy
`bounded_evidence_preparation_policy_binding_identity`, coordinated
configuration/policy resealing, cross-generation binding, each paired-limit
mismatch, and current-readiness/Git reconstruction mismatch.

Measurement-mode evidence proves the exact candidate mode can run only the
bounded preparation pipeline over the exact source envelope and that final
readiness, current-readiness, final Git reconstruction, descriptor, and
registry surfaces reject it. Direct tests distinguish measurement and final
policy identities; accept only the exact pending object; reject null, omitted,
unknown, malformed, or extended markers; reject mode/deferred-vector/
projection-bound/disk-bound substitution and cross-mode resealing; and prove
the four source pairs plus projection pair remain exactly equal. No test helper
may promote or rewrite policy bytes automatically. Post-adoption tests require
measurement-mode rejection and prove that every policy, binding,
source-processing, schema, component, resource, profile, and affected test
identity listed in Section 12 changes and reconstructs from the final bytes.

Unit evidence may run locally. Stable-source mutation tests, RSS measurement,
disk ceiling, Seatbelt capability confinement, worker boundary,
crash/interruption, full 21-member projection, double reconstruction, and
end-to-end Replay evidence must run on the governed sandbox-capable host.
Watchdog behavior must run there after numeric adoption, when its exact values
exist. No skip or sandbox bypass can establish acceptance.

## 17. Slice-3 relationship and sequencing

The exact source graph cannot currently pass governed processing safely, so
this decision is a prerequisite to completing the production Experiment 005
adapter. It is not a scientific experiment revision.

Required order is:

```text
governance clarification freeze
  -> independently verified remote-backed clarification commit
  -> non-authoritative bounded-streaming implementation candidate using measurement mode
  -> governed full-envelope measurement evidence
  -> independent review of measurement evidence
  -> bounded numeric-envelope adoption
  -> dependent identity regeneration
  -> post-adoption exact-byte full-envelope rerun
  -> independent implementation review/freeze
  -> only then later Slice-3 descriptor and readiness boundaries
```

The separate subordinate outcome-gate provenance governance remains an
independent Slice-3 prerequisite and may proceed independently. This decision
does not define or implement it.

## 18. Explicit non-authorizations

This adopted clarification creates no authority for production or test implementation,
source membership changes, C2 inclusion, protocol or scientific revision,
external-input descriptor materialization, Experiment configuration instance,
ranking/evaluation schemas, profile contracts, thin entry point,
implementation binding, adapter creation or adoption, registry modification,
Source S, readiness candidate/evidence/E/R, allocation, provider/control
authority, execution, outcome access or evaluation, confirmation selection,
Paper Miner, wallet, transaction, capital, or SOL work.

This clarification freezes prospective measurement-mode design authority only.
Every successor step remains separately bounded
and independently reviewed.
