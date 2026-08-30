# RQ-003 Experiment 005 Source-Processing Prerequisite v1

## Status

- Type: Prospective subordinate source-processing governance decision
- State: Adopted and frozen prospectively
- Experiment: `rq003-experiment-005-signed-share-imbalance-predictive-evaluation`
- Decision revision: `rq003-experiment-005-source-processing-prerequisite-v1`
- Execution Readiness disposition: `COMPATIBLE WITHOUT READINESS REVISION`
- Source S established: No
- Implementation authorized: No
- Outcome access authorized: No
- Experiment execution authorized: No

## 1. Purpose and authority

This decision prospectively freezes the source convention and input-processing
contract that must exist before a final Source S can be proposed for
Experiment 005. This decision is subordinate to:

- [RQ-003 Experiment 5 — Signed Share Imbalance Predictive Evaluation](../experiments/rq003-experiment-005-signed-share-imbalance-predictive-evaluation.md);
- [RQ-003 Minimum-Effect Scope Clarification v1](rq003-minimum-effect-scope-clarification-v1.md);
- [Experiment Execution Readiness v1.1](../specifications/experiment-execution-readiness-v1.1.md);
- [Execution Readiness v1 Clarification Decision](execution-readiness-v1-clarification-decision.md);
- [Execution Readiness v1.1 Readiness Record v2](execution-readiness-v1.1-readiness-record-v2.md); and
- [RQ-003 Research Execution Specification v2](../specifications/rq003-research-execution-specification-v2.md).

This decision does not amend any scientific estimand, decision point,
population rule, exclusion, measurement, comparator, baseline, inference,
missingness, confirmation, or interpretation rule in the adopted Experiment
005 protocol. If this decision and the protocol appear to conflict, the
protocol controls and implementation must stop for governance.

The source-processing relationship is exactly:

```text
persisted lifecycle record
  -> immutable referenced observation members
  -> deterministic selected decision-time observation
  -> authenticated scientific state
  -> closed outcome-blind projection
  -> generic Replay preparation
```

The lifecycle record alone is not scientific state. A reference, digest,
parsed object, selected object, or projection identity alone cannot substitute
for the complete authenticated relationship.

## 2. Compatibility disposition

The reviewed disposition is `COMPATIBLE WITHOUT READINESS REVISION`. This
decision neither clarifies nor revises Execution Readiness.

Execution Readiness v1.1 Section 9.1 already permits an ordered collection of
regular files and requires a container input to bind exact container bytes,
decoder/parser identity and configuration, and logical schema. Adapter-
declaration v3 already has a closed `governed_decoder` branch whose component
and configuration are selected through finite repository policy. Governed
source scopes already include all executing source at S, and Phase-3B evidence
already binds external-input, snapshot, dataset, projection, component, and
Replay identities.

The exact contracts below close the five compatibility conditions:

1. preauthorization input processing performs no semantic outcome parsing;
2. the convention is compatible with the exact protocol-fixed dataset bytes
   and schema authority rather than a replacement raw format;
3. the positive projection is representable under the governed projection-
   schema validator without silently extending accepted schema semantics;
4. adapter-v3 can select and Phase-3B can invoke one finite governed decoder
   inside the existing capability boundary; and
5. the generic Replay preparer and controller can reconstruct every required
   identity without adding a readiness-record field or evidence kind.

The compatibility disposition does not authorize implementation. Current code
does not invoke the finite decoder and cannot prepare Experiment 005 evidence.
Any implementation that cannot satisfy all five conditions must stop for the
applicable subordinate governance; it may not reinterpret this decision or
revise Execution Readiness silently.

## 3. External-input container convention

### 3.1 One ordered collection

The future Experiment-005 adapter must declare exactly one external input for
the combined lifecycle/observation source. Its adapter-v3 `input_kind` is
`ordered_file_collection`. The declaration and immutable snapshot contain an
identity-bearing ordered collection of regular files under Execution
Readiness v1.1 Section 9. Symlinks, devices, sockets, implicit directory
enumeration, undeclared globbing, and path aliases are prohibited.

Manifest member zero is the lifecycle member. Its logical identifier is
exactly `lifecycle`. Every later member is a referenced-observation member.
Observation-member logical identifiers are NFC strings matching the exact
adapter-v3 identifier grammar `^[a-z][a-z0-9_.-]*$`. No case folding,
transliteration, trimming, or other normalization is permitted. They are
sorted by `(logical_identifier, member_path)` in Unicode code-point order.
Both values are unique. `member_order` is the zero-based manifest position.
The lifecycle member cannot also be an observation member.

This convention binds no new or replacement dataset, current C2 promotion,
operational locator, live path, or provider. The protocol-fixed dataset
identity remains controlling. A later authorized readiness workflow would
still have to bind the actual ordered members and exact bytes without making
an initial-dataset eligibility decision in this decision.

### 3.2 Persisted JSONL framing

Every member is UTF-8 JSONL with no BOM, blank line, CR byte, invalid UTF-8,
duplicate object key, nonfinite number, or unterminated final record. Each
record is one JSON value followed by exactly one LF byte. Source JSON need not
already use canonical object-key order; persisted bytes remain authoritative
and are never replaced by normalized bytes.

The lifecycle member is the exact existing `replay-dataset-v1` persisted
dataset fixed by the adopted protocol, including persisted SHA-256
`7680856bc6a01f9b69be0921d6e66b3f43d5241a38e63b37871b6925c1d59ba7`
and its existing schema/content authority. This decision does not rewrite,
repair, migrate, or invent replacement lifecycle bytes. Sections 4 and 9
define decoder-normalized logical output only; they do not claim that the
existing raw record has those exact top-level fields. Any byte-different raw
lifecycle source or replacement raw schema requires prospective scientific
governance under the adopted protocol.

`source_file` in scientific authority is the observation member's declared
normalized `member_path`. `source_line_number` is its one-based physical JSONL
line. The immutable source coordinate is exactly:

```text
(logical_member_identifier, source_file, source_line_number)
```

The same coordinate cannot occur twice anywhere in the collection.

## 4. Lifecycle logical record

### 4.1 Record order and chronology

Lifecycle records preserve the protocol's canonical immutable round
chronology. For the current Experiment 005 mechanics that order is ascending
`(start_slot, round_id)`. Persisted lifecycle order must equal that order.
Changing the chronology coordinate requires prospective scientific
governance. `first_observed_at_utc` and `last_observed_at_utc` remain audit and
reconstruction metadata; neither controls fold or round chronology. UTC
timestamps use `YYYY-MM-DDTHH:MM:SS[.fraction]Z`, with the shortest exact
fractional representation and no offset spelling other than `Z`. `round_id`
is a nonnegative integer and is unique.

### 4.2 Closed outcome-blind lifecycle core

The persisted record kind is exactly `RoundLifecycleIndexRecord` with
`lifecycle_schema_version=1`, governed by the tracked definitions in
`src/orev3/historical/models.py`, the tracked loader in
`src/orev3/replay/loader.py`, and the protocol-fixed dataset identity. The raw
record is authenticated and remains byte-identical. The following is an exact
raw-to-normalized mapping, not a replacement raw schema:

| Normalized field | Exact raw source and rule |
| --- | --- |
| `source_convention_revision` | Constant `rq003-experiment-005-two-tier-source-v1`. |
| `lifecycle_source_file` | Declared normalized lifecycle-member path. |
| `lifecycle_source_line_number` | One-based physical line in the lifecycle member. |
| `raw_lifecycle_schema_version` | Raw `lifecycle_schema_version`; it must equal integer `1`, with booleans rejected. |
| `round_id` | Raw `round_id` unchanged; nonnegative integer. |
| `start_slot` | Raw `start_slot` unchanged; nonnegative integer. |
| `end_slot_available` | `true` exactly when raw `end_slot` is a nonnegative integer; `false` exactly when it is JSON null. |
| `end_slot` | Raw nonnegative integer unchanged when available; integer `0` when unavailable. The paired boolean makes the unavailable sentinel unambiguous. No end slot is fabricated. |
| `first_observed_at_utc`, `last_observed_at_utc` | Raw fields unchanged after canonical UTC validation; they must equal the first and last canonically ordered authenticated references. |
| `first_observed_rpc_slot`, `last_observed_rpc_slot` | Raw fields unchanged; they must equal the corresponding first and last authenticated reference slots. |
| `observation_count` | Raw integer unchanged and exactly equal to reference count; it must be positive. |
| `normal_observation_count` | Derived integer exactly equal to `observation_count`. Every lifecycle reference must resolve to a tracked-schema record accepted by `normalize_snapshot`; a malformed referenced line rejects the source graph rather than reducing this count. |
| `collector_session_ids` | Raw array, preserving exact identities, normalized only by requiring the already-persisted order to be ascending and duplicate-free; it may be empty under the absence rule below. |
| `source_schema_versions` | Raw ascending duplicate-free array unchanged; every value must be integer `1` or `2` and equal the distinct reconstructed referenced-observation versions. |
| `source_files` | Raw ascending duplicate-free path array unchanged; it must equal the distinct `source_file` values in the authenticated references. |
| `observation_references` | Raw array resolved and authenticated exactly under Sections 4.3 and 5, then ordered by the frozen reference order without changing the raw record. |

Raw `quality.coverage_status` maps exactly as follows:

| Raw value | Normalized lifecycle status | Handling |
| --- | --- | --- |
| `complete` | `complete` | Recognized complete lifecycle. |
| `partial_start` | `partial_start` | Recognized partial lifecycle. |
| `partial_end` | `partial_end` | Recognized partial lifecycle. |
| `partial_both` | `partial_both` | Recognized partial lifecycle. |
| `unknown` | `unavailable` | Existing protocol/data-conformance failure: the four-state lifecycle authority required by Experiment 005 is unavailable, so source processing rejects before Replay and any attempted execution is `invalid_execution`. It is not a fifth scientific population or a new exclusion. |

No other coverage value is accepted. For a raw null `end_slot`, normalized
`end_slot_available=false` and `end_slot=0`; no selected state is constructed,
and the existing governed disposition is exactly
`no_predeclared_decision_observation`. The round may retain reference-only
audit provenance, but it cannot support `end_slot - 5`. No new category is
created.

Quality and cadence fields map exactly:

- raw `quality.initialization_state_observed`,
  `rpc_slot_regression_count`, `largest_rpc_slot_regression`,
  `duplicate_rpc_slot_count`, `significant_gap_count`, and
  `collector_session_count` map unchanged after exact type/range validation;
- `collector_session_count` equals the length of `collector_session_ids`;
- raw `quality.max_observation_gap_seconds` and
  `significant_gap_threshold_seconds` are read from their persisted JSON
  number lexemes as exact nonnegative decimal rationals, multiplied by exactly
  `1_000_000`, and must produce nonnegative integers with no remainder;
- those integers become `max_observation_gap_microseconds` and
  `significant_gap_threshold_microseconds`; NaN, infinity, exponent spelling,
  negative zero, negative values, sub-microsecond values, or a nonintegral
  product reject; and
- the converted maximum and threshold plus raw `significant_gap_count` must
  reconstruct exactly from adjacent canonical observation timestamps, where a
  gap is significant only when it is strictly greater than the threshold.

Raw `quality.finalized_state_observed` and all raw finalized-outcome fields are
outcome-bearing. They are covered by whole-byte authentication but are not
semantically decoded before authorization under Section 4.4.

Collector-session absence is preserved, not repaired. Each normalized
reference contains `collector_session_available`, a boolean, and
`collector_session_id`, a string. Availability true requires a nonempty NFC
identifier; availability false requires the empty string and means the
persisted source legitimately lacks session identity. `collector_session_ids`
is the sorted unique collection of available identifiers and may therefore be
empty. Absence alone is not invalid source and maps to the adopted protocol's
`collector_regime_metadata_unavailable` handling without creating a new
exclusion. When the selected reference lacks session identity, the downstream
selected-source `collector_session_id` is absent.

### 4.3 Observation reference

Each lifecycle `observation_references` member contains exactly:

- `logical_member_identifier`;
- `source_file`;
- `source_line_number`;
- `source_member_identity`;
- `source_member_byte_count`;
- `source_member_sha256`;
- `persisted_record_byte_count`;
- `persisted_record_byte_sha256`;
- `canonical_parsed_observation_identity`;
- `observed_at_utc`;
- `rpc_slot`;
- `source_schema_version`;
- `observation_classification`, exactly `normal`;
- `collector_session_available`; and
- `collector_session_id`.

Collector-session fields obey Section 4.2. Integers reject booleans, negative
values, fractions, exponents, and alternate numeric spellings after parsing.
Every value must equal the independently decoded referenced record.

### 4.4 Raw-versus-normalized and outcome boundary

The lifecycle core is normalized output reconstructed from the fixed raw
dataset. It is not a replacement raw lifecycle schema. In particular, this
decision imposes no invented `outcome_envelope` on existing persisted records.

Before ranking freeze and attempt-local outcome authorization, outcome-bearing
bytes may only be authenticated by the governed outcome-bearing-byte
verification mechanism permitted by Execution Readiness. The decoder,
projection worker, Replay preparer, readiness tests, controller-side
reconstruction, and ranking worker must not instantiate, parse, normalize,
retain, return, or diagnose a semantic outcome record. They may receive only
the permitted digest, byte count, availability-independent sealed source
identity, and immutable snapshot authority. The outcome source remains
separately sealed and inaccessible to those components. It is opened and
parsed only inside the evaluation environment after ranking reconstruction,
ranking freeze, and attempt-local authorization. Projection material binds
source/input identities without embedding outcome availability, value,
provenance, capture mode, or semantic label material.

Preauthorization lifecycle extraction semantically decodes exactly these raw
paths and no others:

```text
lifecycle_schema_version
round_id
start_slot
end_slot
first_observed_at_utc
last_observed_at_utc
first_observed_rpc_slot
last_observed_rpc_slot
observation_count
collector_session_ids
source_schema_versions
source_files
observation_references[*].source_file
observation_references[*].source_line_number
observation_references[*].observed_at_utc
observation_references[*].rpc_slot
quality.coverage_status
quality.initialization_state_observed
quality.rpc_slot_regression_count
quality.largest_rpc_slot_regression
quality.duplicate_rpc_slot_count
quality.max_observation_gap_seconds
quality.significant_gap_count
quality.significant_gap_threshold_seconds
quality.collector_session_count
```

The authenticated observation-member semantic whitelist is exactly:

```text
schema_version
collector_session_id
observed_at_utc
rpc_slot
board.round_id
board.start_slot
board.end_slot
board.production_cost_ema
treasury.motherlode
round.round_id
round.deployed_lamports
round.miner_counts
round.motherlode
round.total_vaulted
round.total_winnings
round.total_miners
```

The extractor authenticates the complete member and record bytes first. It
then validates UTF-8/JSON framing, object/array boundaries, key uniqueness,
and the tracked structural location of every whitelisted field. It decodes and
materializes values only at the paths above. Every other value is traversed as
an opaque structurally bounded JSON token region: its bytes remain inside the
authenticated member/record digests, but its scalar, array, or object value is
not converted into a semantic object, retained, logged, included in a
diagnostic, or returned. In particular lifecycle `finalized_outcome`,
`finalized_outcome_source`, `finalized_outcome_capture_mode`,
`finalized_outcome_evidence_identities`, and
`quality.finalized_state_observed`, plus every nonwhitelisted observation
path, remain opaque.

Raw lifecycle and raw observation decoding inherits the exact tracked parser
and Pydantic-model behavior for extra top-level and nested keys: extra keys
accepted and ignored by that authority do not cause rejection and do not
become normalized scientific fields. Only the explicitly mapped fields above
enter normalized source-processing state. Every ignored extra field remains
covered by persisted-member and persisted-record byte authentication but
cannot influence selection, ranking, eligibility, logical identities,
diagnostics, or projection semantics. A future change to tracked parser or
model extra-field behavior requires a new Source-S revision and binding and
cannot be silently inherited. Stable diagnostics identify only a governed
schema/path rule, never a raw value or excerpt. The later evaluation opener
independently reparses the sealed outcome source only after ranking
reconstruction, ranking freeze, and attempt-local authorization. No readiness
evidence kind or readiness-record field is added by this extraction contract.

## 5. Referenced observation logical record

Each reference resolves the exact raw JSONL line named by raw
`ObservationReference.source_file` and one-based `source_line_number`. The
declared ordered external-input member whose normalized `member_path` equals
that `source_file` supplies the authenticated bytes. Member identity, member
byte count/SHA-256, exact line byte count/SHA-256, manifest position, and
snapshot identity are verified before semantic extraction. Raw reference
`observed_at_utc` and `rpc_slot` must equal the values extracted from that
line.

The accepted raw observation schema authority is exactly
`src/orev3/historical/reader.py::SUPPORTED_SCHEMA_VERSIONS={1,2}` together
with `normalize_snapshot` and the closed normalized models in
`src/orev3/historical/models.py`. Version mapping is exact:

- absent raw `schema_version` or integer `schema_version=1` maps to source
  schema version `1` and collector-session absence; and
- integer `schema_version=2` maps to source schema version `2`; raw
  `collector_session_id` maps unchanged when it is a nonempty NFC string and
  maps to explicit absence when it is null or absent.

Booleans, strings, fractions, and versions other than `1` and `2` reject. The
raw lifecycle `source_schema_versions` array must equal the ascending distinct
set reconstructed under these rules.

The normalized observation has exactly the provenance fields in Section 4.3
and the following outcome-blind scientific fields:

| Normalized field | Exact raw source and rule |
| --- | --- |
| `round_id` | Raw `board.round_id`, which must equal raw `round.round_id` and lifecycle `round_id`. |
| `observed_at_utc` | Raw top-level field after canonical UTC validation. |
| `rpc_slot` | Raw top-level nonnegative integer unchanged. |
| `deployed_lamports` | Raw `round.deployed_lamports`, exactly 25 nonnegative integers in square order `0..24`. |
| `miner_counts` | Raw `round.miner_counts`, exactly 25 nonnegative integers in square order `0..24`. |
| `total_miners` | Raw `round.total_miners`, nonnegative integer equal to the exact sum of `miner_counts`. |
| `active_round_motherlode` | Raw `round.motherlode`; a selected decision requires exact integer `0`. |
| `pre_finalization_total_vaulted` | Raw `round.total_vaulted` at the authenticated selected predecision observation. |
| `pre_finalization_total_winnings` | Raw `round.total_winnings` at the authenticated selected predecision observation. |
| `start_slot` | Raw `board.start_slot`, nonnegative integer equal to lifecycle `start_slot`. |
| `observation_end_slot` | Raw `board.end_slot`; `2^64-1` is the tracked initialization sentinel, otherwise it is a nonnegative initialized end slot. An initialized selected record must equal the available lifecycle `end_slot`. |
| `production_cost_ema` | Raw `board.production_cost_ema`; a selected decision requires a nonnegative integer. Null cannot be repaired and is the existing protocol/data-conformance `invalid_execution` boundary because fundamental state cannot reconstruct. |
| `treasury_motherlode` | Raw `treasury.motherlode`, nonnegative integer unchanged. |
| collector session | Derived exactly by the version rules above and encoded as `collector_session_available` plus `collector_session_id`. |
| `source_schema_version` | Exact version `1` or `2` derived above. |

Every integer rejects booleans. The decoder does not semantically decode raw
`finalized_outcome`, outcome provenance/capture fields, `round.entropy`,
`round.slot_hash_hex`, finalized reward semantics, or any winner/label field
before authorization. Fields required above are decoded only from the
authenticated observation chosen or considered at the predeclared decision
boundary and retain their contemporaneous values.

There is no literal raw observation-classification field. A referenced line is
`normal` exactly when tracked `normalize_snapshot` accepts schema version `1`
or `2`, the reference cross-checks, and all source-integrity rules above pass.
Tracked `read_observer_file` classifies JSON/schema/normalization failures as
`MalformedRecord`; such a line does not become a normalized observation. If a
lifecycle reference names one, the two-tier graph is incomplete and source
processing rejects. This is source conformance, not a new scientific
exclusion. No decoder-defined `invalid_reason` or third classification exists.

A normal record with `rpc_slot < start_slot` or, for an initialized lifecycle,
`rpc_slot > end_slot` has a true round/slot contradiction and rejects. A normal
record with `end_slot - 5 < rpc_slot <= end_slot` remains authenticated
reference-only audit provenance but cannot be selected. Future-to-decision
status alone is not source invalidity.

## 6. Persisted-byte and logical identities

### 6.1 Canonical function

For identities defined here, `canonical(x)` is UTF-8 JSON with NFC strings,
objects keyed in Unicode code-point order, arrays in semantic order, integers
in minimal base-10 form, no whitespace, no null or floating-point value, and
exactly one terminal LF. Duplicate keys, unknown fields, missing fields,
noncanonical paths, invalid Unicode, and values outside the closed schema
reject before hashing.

`D(domain, x)` means lowercase hexadecimal:

```text
SHA256(UTF8(domain + "\n") || canonical(x))
```

No NUL, length, alternate separator, or extra newline is inserted.

### 6.2 Required distinct identities

The following identities are separate and cannot substitute for one another:

| Object | Governing identity |
| --- | --- |
| Persisted lifecycle member bytes | adapter-v3 member SHA-256, byte count, member identity, manifest identity, external-input identity, and immutable-snapshot identity |
| Persisted observation-member bytes | the corresponding adapter-v3 member SHA-256, byte count, member identity, manifest identity, external-input identity, and immutable-snapshot identity |
| Persisted JSONL record bytes | SHA-256 of the exact record bytes including its one LF, plus exact byte count and immutable coordinate |
| Parsed lifecycle core | `D("orev3:rq003-experiment-005:lifecycle-record:v1", lifecycle_core)` |
| Parsed referenced observation | `D("orev3:rq003-experiment-005:referenced-observation:v1", referenced_observation)` |
| Selected observation | `D("orev3:rq003-experiment-005:selected-observation:v1", selected_material)` |
| Selected scientific state | `D("orev3:rq003-experiment-005:selected-scientific-state:v1", scientific_state)` |
| Projection record | `D("orev3:rq003-experiment-005:projection-record:v1", projection_record)` |
| Projection bytes | ordinary SHA-256 and byte count of the complete canonical JSONL |
| Logical projection content | `D("orev3:rq003-experiment-005:projection-content:v1", {"ordered_projection_record_identities":[...],"record_count":N})` |

`selected_material` contains the parsed lifecycle identity, complete selected
reference, parsed referenced-observation identity, selected canonical
observation index, and decision-selection identity. `scientific_state`
contains the selected-observation identity, exact decision snapshot identity,
the 25 fundamental MeasurementVector identities in square order, and the
decision-point configuration identity.

The generated projection's ordinary SHA-256 does not replace its logical
content identity, projection-evidence identity, readiness projection identity,
or dataset identity. Normalization never changes, drops, or redefines any
persisted digest, byte count, coordinate, manifest position, or snapshot
identity.

## 7. Decoder and normalizer contract

### 7.1 Capability and authority

The future decoder is a finite repository-governed component selected by
adapter-v3. Its exact implementation path/blob/SHA-256, revision, worker kind,
and component identity, and its exact configuration path/blob/SHA-256, byte
count, and configuration identity, must reconstruct at S. It executes only in
the `INPUT_PROJECTOR` capability boundary over immutable preparation or launch
snapshots. Descriptors may select only its finite identifier, never a module,
path, callable, callback, or arbitrary hash tuple.

The configuration must bind this decision revision, source-convention
revision, raw lifecycle schema identity, raw observation schema identities,
projection schema identity, decision-selection identity, supported protocol
revision, candidate order, resource bounds, and the identity domains in
Section 6.

### 7.2 Required processing

The decoder must, in this order:

1. authenticate the adapter declaration, ordered manifest, every immutable
   member byte count and digest, and the complete snapshot identity;
2. enforce JSONL framing and authenticate the fixed lifecycle source schema,
   version, bytes, and outcome-bearing-byte verification without instantiating
   semantic outcome material;
3. extract only the governed outcome-blind lifecycle fields in persisted line
   order and reconstruct their canonical logical identities;
4. resolve every observation reference by exact declared member and line;
5. authenticate the exact referenced record bytes before parsing them;
6. validate the referenced schema/version and reconstruct its logical identity;
7. require every lifecycle/reference field and identity to cross-match;
8. validate timestamps, slots, arrays, cardinality, integers, totals,
   classifications, sessions, schemas, round fields, and chronology;
9. sort references by `(observed_at_utc, source_file, source_line_number)` and
   assign zero-based `observation_index` in that order;
10. reconstruct lifecycle counts, session/schema sets, and gap metadata;
11. select the decision reference under Section 8;
12. for a selected reference, reconstruct the exact decision snapshot and all
    25 fundamental MeasurementVectors before deriving selected identities;
13. emit one closed outcome-blind projection record per lifecycle record in
    lifecycle order; and
14. return no semantic outcome object, value, metadata, diagnostic, handle,
    parser, opener, or retained semantic outcome state.

The decoder must be deterministic and must produce identical rejection or
identical canonical projection bytes on repetition from identical authority.
Diagnostics use bounded stable codes and must not include raw record values,
outcomes, locators, credentials, or source excerpts.

### 7.3 Duplicate, missing, and invalid-source semantics

The following reject the complete source graph before Replay:

- missing or extra manifest members relative to adapter authority;
- missing lifecycle member, referenced member, or referenced line;
- a reference to member zero or an undeclared member;
- byte-count, digest, schema, version, identity, chronology, or cross-reference
  mismatch;
- duplicate lifecycle round identity or `round_id`;
- duplicate immutable source coordinate;
- duplicate reference identity within the lifecycle reference graph;
- one persisted coordinate claimed by more than one lifecycle record;
- conflicting claims over one persisted coordinate;
- malformed JSON, unsupported schema, invalid normal record, or incomplete
  source graph; and
- source substitution before, during, or after snapshot authentication.

Distinct authenticated coordinates remain distinct observations even when
their persisted bytes or normalized semantic content are identical. Duplicate
coordinates reject. Duplicate reference identities reject. Conflicting claims
over one coordinate reject. Reuse of one reference by multiple lifecycle
records rejects because each structural-round source graph owns its reference
coordinates. No observation is merged, deduplicated, overwritten, or repaired
solely because its bytes or semantic content match another observation.

Missing valid decision state is not invalid source: it produces the existing
protocol disposition `no_predeclared_decision_observation`. No new scientific
exclusion is created by this decision.

## 8. Decision-selection contract

There is exactly one scientific decision per eligible lifecycle round.
Selection uses the complete authenticated reference graph and no outcome:

1. if `end_slot_available=false`, emit no selected scientific state and the
   exact disposition `no_predeclared_decision_observation`; the integer-zero
   representation is not evaluated as an end slot;
2. otherwise retain references whose classification is `normal` and whose
   `rpc_slot` is at or before the available `end_slot - 5`;
3. if none remain, emit no selected scientific state and the exact disposition
   `no_predeclared_decision_observation`;
4. otherwise choose the greatest `rpc_slot`; and
5. among references at that slot, choose the last under ascending
   `(observed_at_utc, source_file, source_line_number)`.

This equal-RPC rule is the adopted canonical source ordering. It cannot be
replaced by lifecycle line order, manifest order, filesystem order, RPC return
order, observation index supplied by source data, or outcome knowledge.

References after the boundary remain authenticated audit provenance but cannot
become selected state; their future-to-decision status alone is not invalid.
True round/slot contradictions remain invalid under Section 5.
An incomplete or unauthenticated graph rejects; it cannot be converted to the
missing-decision disposition. The selected decision must reconstruct from the
same reference, parsed observation, decision snapshot, fundamental vectors,
and identities in every downstream representation.

## 9. Closed outcome-blind projection

### 9.1 Container and order

The projection is canonical newline-terminated JSONL. It contains exactly one
record per lifecycle record, in lifecycle chronology. It has no blank lines,
BOM, alternate JSON spelling, or trailing bytes after the final LF. Projection
record order is semantic and participates in projection identities.

### 9.2 One fixed current-validator-compatible schema

There is one top-level object schema. It has `type="object"`,
`additionalProperties=false`, and `required` equal to the complete
`properties` set. Every nested object has the same closed/all-required rule.
The schema uses only the currently governed validator keywords `$id`,
`$schema`, `type`, `properties`, `required`, `additionalProperties`, `items`,
`minItems`, `maxItems`, `minLength`, `maxLength`, `minimum`, `maximum`,
`pattern`, `enum`, `const`, and `uniqueItems`. It uses no `oneOf`, `anyOf`,
`allOf`, `if`, `then`, `else`, nullable field, omitted branch property, or
implementation-defined extension.

Every record requires exactly these top-level properties:

- provenance/control: `projection_schema_version=1`, `source_unit_key`,
  `lifecycle_source_file`, `lifecycle_source_line_number`,
  `lifecycle_member_identity`, `lifecycle_record_byte_count`,
  `lifecycle_record_byte_sha256`, `canonical_lifecycle_record_identity`,
  `external_input_identifier`, `external_input_identity`,
  `ordered_collection_manifest_identity`,
  `immutable_input_snapshot_identity`, `decoder_component_identity`,
  `decoder_configuration_identity`, `parser_component_identity`,
  `projector_component_identity`, `projection_schema_identity`,
  `decision_selection_identity`, `dataset_version`, `protocol_revision`, and
  `research_execution_specification_revision`;
- lifecycle: `round_id`, `start_slot`, `end_slot_available`, `end_slot`,
  `first_observed_at_utc`, `last_observed_at_utc`, `lifecycle_status`,
  `observation_count`, `normal_observation_count`,
  `initialization_state_observed`, `rpc_slot_regression_count`,
  `largest_rpc_slot_regression`, `duplicate_rpc_slot_count`,
  `significant_gap_count`, `max_observation_gap_microseconds`,
  `significant_gap_threshold_microseconds`, `collector_session_count`,
  `collector_session_ids`, `source_schema_versions`, `source_files`, and
  `observation_references` containing every Section 4.3 field plus its
  zero-based canonical `observation_index`;
- generic Replay: `candidates`, exactly `[0,1,...,24]`, `selected`,
  `eligible`, `exclusion_reason`, and `observation_index`; and
- selected-state containers: `selected_references`,
  `selected_observation_identities`, `selected_scientific_state_identities`,
  `selected_snapshot_identities`,
  `fundamental_measurement_vector_identities`, `deployed_lamports`,
  `miner_counts`, `total_miners_values`,
  `active_round_motherlode_values`,
  `pre_finalization_total_vaulted_values`,
  `pre_finalization_total_winnings_values`,
  `production_cost_ema_values`, and `treasury_motherlode_values`.

`source_unit_key` is exactly the base-10 ASCII decimal representation of the
record's nonnegative integer `round_id`: no sign; no leading zero except the
exact value `0`; characters limited to ASCII `0` through `9`; no whitespace,
prefix, suffix, separator, or locale-dependent formatting; and UTF-8 bytes
equal to the ASCII bytes of that string. Parsing the key as base-10 must
round-trip exactly to `round_id`. The projector, generic Replay preparer, and
input-processing controller must independently reconstruct this value and
verify equality rather than accept it as an unconstrained source identifier.

All selected-state containers are arrays in both states. Their element schemas
are fixed and closed. `selected_references` items contain exactly the Section
4.3 reference fields plus `observation_index`; identity arrays contain
lowercase 64-hex strings; numeric arrays contain nonnegative integers and
reject booleans.

The controller enforces exactly one of these two semantic states without a
schema branch:

| Field | Selected state | Nonselected state |
| --- | --- | --- |
| `selected`, `eligible` | both `true` | both `false` |
| `exclusion_reason` | `not_applicable` | `no_predeclared_decision_observation` |
| `observation_index` | selected zero-based canonical index | integer `0`, a sentinel disambiguated by both booleans being false |
| `selected_references` | length 1 | empty array |
| each of the three selected/snapshot identity arrays | length 1 | empty array |
| `fundamental_measurement_vector_identities` | length 25 in square order | empty array |
| `deployed_lamports`, `miner_counts` | length 25 in square order | empty arrays |
| each `*_values` scalar container | length 1 | empty array |

The “three selected/snapshot identity arrays” are
`selected_observation_identities`, `selected_scientific_state_identities`, and
`selected_snapshot_identities`. Empty arrays cannot represent a selected
scientific value because selected state requires the exact nonempty lengths;
the nonselected observation-index zero cannot be confused with valid selected
index zero because `selected=false`, `eligible=false`, and every selected-state
container is empty. The schema sets each array's `minItems=0` and its exact
maximum (`1` or `25`) using supported keywords; the finite governed projector
and controller enforce the exact state-dependent cardinalities above and
reject every intermediate length. Null, missing properties, scalar sentinels,
and additional properties are prohibited.

For a raw null lifecycle end slot, the projection has
`end_slot_available=false`, `end_slot=0`, the nonselected state, and
`exclusion_reason="no_predeclared_decision_observation"`. For an available end
slot it has `end_slot_available=true` and preserves the raw integer. The
paired boolean prevents the zero sentinel from being interpreted as a real end
slot.

`dataset_version` is exactly `replay-dataset-v1` under the adopted protocol.
`research_execution_specification_revision` is exactly
`rq003-research-execution-specification-v2`. `protocol_revision` equals the
single supported homogeneous source revision bound by the future adapter and
dataset declaration; this decision does not select different source bytes or
permit pooling. `decision_selection_identity` must reconstruct from the
adopted boundary, candidate order, selection rule, and equal-RPC order rather
than be accepted as a literal.

The projection record deliberately excludes projection-byte identity,
projection-content identity, dataset identity, Replay identity, selected-
decision identity, and `selected_source_projection_binding_identity`. Each is
downstream of the projection bytes or Replay reconstruction and embedding it
would create a cycle. Existing Phase-3B dataset/projection evidence binds the
projection to external input, snapshot, parser, projector, schema, byte, and
record-count authority. After projection and Replay identities reconstruct,
the input-processing controller constructs `SelectedSourceProjectionBinding`
from those evidence roots and the selected projection fields. That binding
must cover the actual upstream external-input, member, persisted-record,
parsed-record, decoder, projection, dataset, Replay-source, selected-decision,
selected-reference, selected-snapshot, and fundamental-vector authority.
Synthetic identity-shaped values are prohibited. The binding is supplied to
ranking with the selected scientific state; it is not serialized back into
the projection.

### 9.3 Prohibited projection material and capabilities

Neither a projection record, projection schema, projection evidence,
projection diagnostic, Replay request, nor ranking input may contain, derive,
or expose:

- winner, winning square, finalized outcome, label, or `won`;
- outcome availability, provenance, capture mode, source, or locator;
- evaluation result, interpretation, or post-outcome disposition;
- raw outcome bytes or an outcome opener, parser, provider, resolver, joiner,
  callback, authorization, or evaluation capability; or
- a filesystem/provider capability able to reacquire raw input or outcomes.

The positive field list in Section 9.2 is exhaustive. Case, nesting, aliases,
encoded values, free-form metadata, notes, and generic extension objects do
not evade this prohibition. Recursive forbidden-key and capability tests must
fail closed.

## 10. Replay relationship

The Replay contract is Model 1. No Experiment-005-specific Replay preparer is
authorized by this decision.

The governed decoder/normalizer authenticates the full two-tier graph and
emits the flat projection in Section 9. The generic Replay preparer receives
only the verified projection bytes and projection schema. It receives no raw
snapshot, locator, semantic outcome material, decoder capability, or input
opener.

For each `source_unit_key`, the projection contains one round-level record.
The generic preparer's existing `eligible` and `exclusion_reason` interface
therefore validates the already-governed selection: an eligible record is the
unique selected decision; a noneligible record carries the sole permitted
missing-decision disposition. The preparer must preserve lifecycle record
order, candidate order, projection identity, dataset identity, decision-
selection identity, source-unit identity, and population disposition. It must
reconstruct and cross-check the selected decision. The input-processing
controller must then construct and cross-check
`SelectedSourceProjectionBinding` from the projection and completed Replay
evidence before ranking receives either object. Neither component may perform
a different source selection or trust identity-shaped fields without roots.

The generic Replay preparer remains usable because the record retains its
existing `source_unit_key`, `candidates`, `selected`, `eligible`,
`exclusion_reason`, and `observation_index` interface. The fixed additional
lifecycle, provenance, reference, and selected-state containers are verified
and reconstructed by the finite governed Experiment-005 input-processing
controller; the generic preparer does not reinterpret them. No replacement
Replay preparer, new readiness-record field, or new evidence kind is required.
The governed decoder invocation and the bounded controller reconstruction
remain subordinate implementation work and are not authorized here.

## 11. Required future conformance tests

If a later implementation is separately authorized, synthetic outcome-free
fixtures must prove at least:

1. exact lifecycle and observation persisted-byte counts and SHA-256 values;
2. lifecycle-to-observation cross-reference reconstruction across multiple
   ordered members;
3. malformed JSON, unsupported schema/version, invalid integer/boolean,
   cardinality, total, timestamp, slot, and cross-round rejection;
4. missing/extra member, line, reference, and incomplete-graph rejection;
5. duplicate coordinate, reference identity, lifecycle round, member path,
   logical identifier, and conflicting-coordinate rejection;
6. preservation of repeated-but-distinct observations;
7. exact lifecycle chronology and reference source ordering;
8. latest-at-or-before-boundary selection and missing-decision disposition;
9. equal-RPC ordering by timestamp, source file, and source line;
10. true round/slot-contradiction rejection and preservation-but-nonselection
    of future-to-decision observations;
11. all identity domains and cross-layer identity reconstruction;
12. byte-for-byte canonical JSONL projection reproduction;
13. projection record order and logical-content identity reconstruction;
14. recursive outcome-field, alias, encoded-value, and metadata leakage
    rejection;
15. rejection of raw locator, filesystem, outcome, join, evaluation, and
    callback capability leakage;
16. deterministic repeated decoder and Replay reconstruction;
17. persisted member, record, manifest, schema, component, configuration,
    snapshot, projection, and dataset substitution rejection;
18. replacement of synthetic `SelectedSourceProjectionBinding` roots with
    actual authenticated synthetic fixture roots;
19. selected reference, snapshot, vectors, decision, and binding mismatch
    rejection;
20. `INPUT_PROJECTOR` isolation and bounded diagnostic behavior;
21. raw null-`end_slot` and every exact `coverage_status` mapping, including
    rejection of `unknown` as unavailable source authority;
22. exact lifecycle schema version `1`, exact referenced-observation versions
    `1` and `2`, collector-session presence and explicit absence, and rejection
    of every other version;
23. whitelist-only preauthorization semantic extraction while all bytes,
    including opaque outcome-bearing regions, remain authenticated;
24. exact selected and nonselected fixed-shape projection states, including
    empty-container and observation-index-zero disambiguation; and
25. Replay-boundary conformance proving the generic preparer receives only the
    closed projection and produces identical ordered source, decision, Replay,
    and population authority.

Tests must not open or fabricate real outcomes, select the initial dataset,
or execute Experiment 005.

## 12. Explicit non-authorizations

This decision creates no authority for:

- actual initial Experiment-005 dataset selection or C2 dataset promotion;
- decoder, normalizer, projection, adapter, descriptor, artifact/output
  declaration, experiment entry-point, or registry implementation;
- production adapter or production registry membership;
- final Source S or a claim that current code can prepare it;
- readiness evidence, readiness candidate, `READINESS_VALIDATED`, E, R,
  `EXECUTION_READY`, launch, provider, backend, allocation, control storage,
  namespace, or `STARTED`;
- Experiment-005 ranking, evaluation, execution, outcome access, Observer-data
  eligibility decisions, or confirmation-dataset selection;
- Strategy admission, Decision Engine, Portfolio Simulator, Paper Miner, Live
  Miner, wallet, transaction, capital, or SOL work; or
- a change to Execution Readiness v1.1, its evidence kinds, identity domains,
  lifecycle states, or outcome boundary.

This decision grants no implementation or downstream authority. A coordinator
may separately authorize a bounded source-processing implementation slice.
Such a later authorization would still have to bind
actual reviewed source, schema, component, configuration, adapter, and test
bytes at its candidate S and could not begin scientific execution.
