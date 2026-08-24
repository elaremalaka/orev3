# Execution Readiness v1.1 — Detached Phase-3B Evidence Publication and Retrieval

Status: Proposed for targeted adversarial review

## 1. Scope and subordinate authority

This decision resolves only the prospective durability and retrieval boundary
for the complete detached Phase-3B evidence used to establish
`READINESS_VALIDATED`. It is additive and subordinate to:

- the [Execution Readiness v1.1 specification](../specifications/experiment-execution-readiness-v1.1.md);
- the [Execution Readiness clarification decision](execution-readiness-v1-clarification-decision.md);
- the [readiness-test-policy-v2 decision](execution-readiness-v1.1-readiness-test-policy-versioning.md);
- the [prerequisite-authority decision](execution-readiness-v1.1-prerequisite-authority-identities.md);
- the [readiness-record-v2 decision](execution-readiness-v1.1-readiness-record-v2.md);
- the [zero-input Phase-3B evidence decision](execution-readiness-v1.1-zero-input-phase3b-evidence.md); and
- the [Phase-3C intermediate checkpoint](../../project-checkpoints/ore-v3-execution-readiness-phase3c-intermediate.md).

The frozen authority chain and Slices 1 through 4 otherwise remain unchanged.
This decision does not amend readiness-record-v2, change an evidence identity,
rerun scientific preparation, create a lifecycle state, or authorize launch,
allocation, control, outcome, evaluation, or execution work.

The governing source digests at proposal time are:

| Authority | SHA-256 |
| --- | --- |
| Phase-3C intermediate checkpoint | `5800b9daf5a9625672966e24ee8f42240cea6e72685e6292285d602fa6e9cff9` |
| Execution Readiness v1.1 | `e938499cc254ce2d65fce925fb6e33c5d8b9dcea73a91a2c01e1017e8fb17da9` |
| Clarification decision | `ce9e7cd57df0d31db5aea0c7674edc3b3b717b96a790d5c7e3075364df151477` |
| Readiness-test-policy-v2 decision | `e0d79b517b126633bb2f39448c61a84307dfd3b51628a39c8501eb7653fe20fd` |
| Prerequisite-authority decision | `50c5bfbfa419ffe723665bbe9e853f98ec301e47a13f6ec55adcf03d9d01f88c` |
| Readiness-record-v2 decision | `debe9e0f91e3f420ad673ced84890071f0123cfe8ab159d20a08973c09817cb3` |
| Zero-input Phase-3B evidence decision | `1c70699297837ab18f1081075626f2fa4d2d586607f2dd3a25d930ea212538ef` |

## 2. Problem and core decision

Readiness-record-v2 intentionally contains normalized direct material and
subordinate evidence identities rather than complete evidence objects. Slice 4
establishes `READINESS_VALIDATED` using the complete detached evidence, but
neither the successful result nor the existing Phase-3B controller durably
publishes that graph. Current readiness must independently reconstruct the
evidence and must not rerun projection, Replay preparation, or other scientific
evidence production.

For fresh prospective v1.1 authority governed by this decision, a successful
`READINESS_VALIDATED` result MAY therefore be followed by publication of the
exact complete canonical detached Phase-3B evidence graph in one dedicated Git
commit `E`.

The authority history is:

```text
S
  -> zero or more first-parent commits not touching this graph root
  -> E
  -> zero or more first-parent commits not touching this graph root
  -> R
  -> zero or more first-parent commits not touching this graph root
  -> H
```

`S` is the source commit bound by the record. `E` is the qualifying evidence
publication commit. `R` retains its existing readiness-seal meaning. `H` is the
single freshly fetched approved remote head used by current readiness.

`E` is publication and durability authority only. It is not:

- a readiness lifecycle state or disposition;
- a readiness identity or second evidence aggregate identity;
- scientific evidence beyond the already-fixed published objects;
- a readiness seal;
- a launch or input snapshot;
- an attempt, allocation, namespace, or control object; or
- an outcome, evaluation, or execution object.

`READINESS_VALIDATED` is established before publication. Publication failure
creates no later readiness authority. No caller assertion that a graph is
complete can substitute for the governed reconstruction and Git history.

## 3. Canonical evidence namespace

### 3.1 Root path

For normalized experiment identifier `X` and lowercase 64-hex
`evidence_preparation_identity` `A`, the one canonical graph root is:

```text
docs/research/readiness/evidence-v1/X/A/
```

`X` MUST equal the experiment identifier in the validated readiness record.
`A` MUST equal `validation.evidence_preparation_identity` in that record and
the independently reconstructed evidence-preparation-v2 identity.

The prefix, experiment component, and identity component are literal
repository-relative POSIX path components. No component may be percent
encoded, case folded, aliased, symlinked, discovered from the filesystem, or
selected by a caller. The existing experiment-identifier normalization and
repository-path safety rules apply. `A` is lowercase hexadecimal and admits no
path separator.

### 3.2 Exact paths

The aggregate root object is exactly:

```text
docs/research/readiness/evidence-v1/X/A/aggregate.json
```

Every subordinate evidence object is stored at:

```text
docs/research/readiness/evidence-v1/X/A/objects/K/I.json
```

where `K` is exactly one of these semantic-kind tokens and `I` is that
object's independently reconstructed lowercase 64-hex identity:

1. `immutable-input-snapshot`;
2. `dataset-validation-evidence`;
3. `outcome-blind-projection-evidence`;
4. `replay-evidence`;
5. `population-accounting-evidence`;
6. `readiness-test-evidence`;
7. `profile-conformance-evidence`; or
8. `artifact-declaration-evidence`.

Every required worker bundle is stored at:

```text
docs/research/readiness/evidence-v1/X/A/workers/W.json
```

where `W` is the independently reconstructed lowercase 64-hex worker-evidence
identity.

No index, alias, `latest` link, alternate extension, empty-directory marker,
README, manifest duplicate, symlink, submodule, executable file, or additional
file is permitted below the graph root. Every graph file MUST be a regular Git
blob with mode `100644`.

The complete allowed path set is derived from the aggregate and closed graph
rules below. Paths compare by exact UTF-8 bytes. Publication and validation
sort paths by ascending UTF-8 byte sequence whenever an ordered path vector is
needed.

## 4. Evidence-preparation aggregate as graph root

The canonical `evidence-preparation-v2` object is the sole graph root and
manifest. Its existing identity remains:

```text
orev3:experiment-evidence-preparation:v1\n
```

No transport identity, bundle identity, second aggregate, or new readiness
identity is created.

`aggregate.json` MUST contain the exact canonical evidence-preparation-v2
bytes whose embedded `evidence_preparation_identity` is `A`. Current readiness
starts from the sealed record's `A`, derives the Section 3 root path, loads
`aggregate.json`, selects the prospective schema revision from the record's
independently validated 29-member registry, reconstructs `A`, and then derives
the complete expected subordinate and worker path set from the aggregate.

The aggregate's identity vectors are membership authority, not proof that the
referenced objects are valid. Every referenced object MUST be loaded,
canonically parsed, schema/Python validated, independently reconstructed, and
cross-bound to the direct readiness record and committed authority at `S`.

## 5. Canonical object bytes

### 5.1 Schema-governed evidence objects

Each schema-governed evidence file contains exactly the existing canonical
JSON object for its selected prospective schema revision, serialized by the
frozen canonical serializer as UTF-8 with sorted object keys, no insignificant
whitespace, and exactly one final LF.

The embedded identity field MUST equal the filename identity `I`. Recomputing
the existing domain-separated identity after excluding only the identity field
already excluded by that object's frozen formula MUST reproduce `I`.

The prospective registry selected by the sealed record determines the schema:

- `immutable-input-snapshot-v1`;
- `dataset-validation-evidence-v1`;
- `outcome-blind-projection-evidence-v1`;
- `replay-evidence-v2`;
- `population-accounting-evidence-v2`;
- `readiness-test-evidence-v1`;
- `profile-conformance-evidence-v2`;
- `artifact-declaration-evidence-v1`; and
- `evidence-preparation-v2` for `aggregate.json`.

Unknown fields, noncanonical bytes, wrong schema generation, missing final LF,
alternate encodings, duplicate JSON keys, and internally rehashed but
first-order-false material are invalid.

### 5.2 Worker publication bundle

A worker publication bundle is a non-registry canonical transport object. It
does not create or revise a worker identity. Its closed object contains exactly
these four fields:

```json
{
  "command_material": {},
  "result_material": {},
  "transport_revision": "phase3b-worker-publication-bundle-v1",
  "worker_material": {}
}
```

The displayed empty objects indicate the governed nested mappings described
below; they are not permitted empty values in a conforming bundle.

The bundle uses the same canonical UTF-8 JSON serialization and final LF as
the evidence objects. Its path identity `W` is not an identity of the wrapper.
`W` MUST equal the existing worker-evidence identity reconstructed from
`worker_material` under:

```text
orev3:phase3b-worker-evidence:v1\n
```

`worker_material` is the exact closed material used by the already-governed
worker formula plus its `worker_evidence_identity` field equal to `W`.
Reconstruction excludes only `worker_evidence_identity`.

For ordinary Phase-3B and readiness workers, `command_material` contains
exactly:

1. `command`;
2. `invocation_identifier`; and
3. `worker_kind`.

For the prospective normalized Phase-3A validator it contains exactly:

1. `authority_generation`, exactly `prospective-v1.1-phase3a`;
2. `command`, exactly `validate_runtime`;
3. `invocation_identifier`, exactly `phase3a-validate-runtime`;
4. `worker_kind`, exactly `PHASE3A_VALIDATOR`; and
5. `worker_revision`, exactly `phase3a-normalized-worker-v1`.

The command identity reconstructed from this exact command material MUST equal
`worker_material.command_identity`.

`result_material` is the exact closed canonical result/output mapping used to
derive `worker_material.output_identity`. For the normalized Phase-3A worker
it is the exact `phase3a-normalized-output-v1` material. For every other worker
it is the successful result mapping emitted by the governed worker command.
The existing worker-evidence domain derives the output identity.

The non-Phase-3A successful result branches are closed as follows:

| Worker command | Exact `result_material` fields |
| --- | --- |
| `project_canonical_jsonl` | `byte_count`, `dataset_content_identity`, `record_count`, `sha256`, `status` |
| `reconstruct_replay` | `byte_count`, `population_identity`, `replay_identity`, `sha256`, `status` |
| readiness `collect` or `run_exact` | `collected_node_ids`, `exit_code`, `results`, `status`, `warning_count` |

For all three branches, `status` is exactly `evidence_passed`. Collection and
result ordering retains the frozen worker semantics. The normalized Phase-3A
result branch contains exactly the closed output field set frozen in the
zero-input Phase-3B decision, including its authority generation and output
revision, and excludes `closed_dependency_root_path` and every equivalent
operational locator.

The validator MUST independently reconstruct and cross-bind, as applicable:

- capability-policy identity;
- closed dependency-environment identity;
- code-capability Git identities;
- command identity;
- input-capability identities;
- invocation identity;
- output identity;
- runtime-contract identity;
- sandbox-template identity;
- source commit;
- successful disposition;
- worker kind and revision;
- worker-module Git identity; and
- committed command/module/code authority at `S`.

Operational request paths, raw stdout/stderr, logs, exception text, temporary
roots, checkout paths, PIDs, timestamps, environment diagnostics, and hostnames
MUST NOT appear.

## 6. Complete graph membership

The required path set is exact. Every aggregate identity has exactly one
corresponding canonical file. Every file below the root is required by one
aggregate identity. Missing, duplicate, unreferenced, or extra files are
invalid.

Committed source components, schema files, policies, contracts, and semantic
component implementations already reachable at `S` are reconstructed from Git
and are not copied into the graph. The zero-input projection authority is a
derived identity and is not published as projection evidence. Raw input bytes
and projected payload bytes are not evidence-object files and are not
published.

### 6.1 Zero-input graph

For the already-governed zero-input branch, the graph contains exactly:

1. `aggregate.json`, containing evidence-preparation-v2;
2. one replay-evidence-v2 object;
3. one population-accounting-evidence-v2 object;
4. one readiness-test-evidence-v1 object;
5. one profile-conformance-evidence-v2 object;
6. one artifact-declaration-evidence-v1 object; and
7. exactly four worker bundles:
   - normalized Phase-3A `validate_runtime`;
   - readiness collection `collection-a`;
   - readiness collection `collection-b`; and
   - readiness execution `execution`.

There are no immutable-input-snapshot, dataset-validation, or projection
evidence files. Their aggregate vectors are exactly `[]`. There is no
parser, dataset-validator, projector, Replay selector, Replay preparer,
profile-validator, or artifact-validator worker bundle.

The aggregate semantic-component vector remains the exact sorted unique
identities of:

- `canonical-replay-preparer-v1`;
- `latest-eligible-observation-selector-v1`;
- `static-profile-validator-v1`; and
- `static-artifact-validator-v1`.

The selector and preparer are committed semantic authority without invocation.
The empty Replay and population, zero-input projection authority, exact four
workers, and exact four semantic components MUST reconstruct under the
zero-input decision.

### 6.2 Nonzero graph

For a nonzero prospective adapter, the graph contains:

1. `aggregate.json`;
2. exactly one immutable-input-snapshot object for each aggregate snapshot
   identity;
3. exactly one dataset-validation object for each aggregate dataset identity;
4. exactly one projection-evidence object for each aggregate projection
   evidence identity;
5. exactly one replay-evidence-v2 object;
6. exactly one population-accounting-evidence-v2 object;
7. exactly one readiness-test-evidence-v1 object;
8. exactly one profile-conformance-evidence-v2 object;
9. exactly one artifact-declaration-evidence-v1 object; and
10. exactly one worker bundle for every aggregate worker identity.

The graph preserves the adapter-declaration order, snapshot member order,
dataset and projection cross-bindings, Replay candidate/source/unit/decision
order, population positional reconciliation, artifact dependency order,
readiness result order, sorted unique semantic-component vector, and sorted
unique worker vector already governed by Phase 3B.

Every parser, dataset-validation, projector, Replay-preparation, normalized
Phase-3A, and readiness worker that actually contributed to the aggregate MUST
be present. A worker not present in the aggregate MUST NOT be published below
the root. Profile and artifact validators remain semantic components rather
than worker evidence unless the independently reconstructed aggregate under
future frozen authority expressly contains such workers.

## 7. Publication authority and preconditions

The prospective publication operation accepts only an internally governed
successful Slice-4 evaluation context containing:

- a `READINESS_VALIDATED` result;
- the exact canonical candidate bytes and readiness identity from that result;
- the complete detached evidence graph used by that evaluation;
- the independently established `S`, experiment, repository authority, and
  approved ref; and
- the explicitly selected prospective registry and serializer.

No production caller may supply `S`, `E`, `R`, graph root, aggregate identity,
worker identities, canonical serializer, schema generation, or invariant
results as authoritative choices.

Immediately before constructing a publication commit, the operation MUST:

1. reparse the exact successful candidate bytes;
2. reconstruct its readiness identity;
3. independently validate its repository/Git/evidence bindings using the same
   frozen Slice-3/Slice-4 primitives;
4. require that its `S`, experiment, adapter, profile, registry, and aggregate
   equal the publication context;
5. validate every canonical evidence and worker-bundle byte sequence;
6. prove exact graph closure and the Section 3 path set;
7. prove absence of prohibited data and path forms; and
8. prove that the bytes to publish are byte-for-byte the evidence used by the
   successful evaluation.

Publication performs no scientific preparation, projection, Replay, test
execution, profile evaluation, or artifact production.

## 8. Qualifying evidence-publication commit E

`E` is the full Git commit identity of the unique qualifying graph-introduction
commit. It has no separate JSON identity and commit-message text grants no
authority.

Git author, committer, timestamp, and message fields participate in the normal
Git commit identity but create no evidence semantics and are never copied into
evidence or readiness material. Implementations need not predict `E` before
publication; they deterministically derive the one authoritative `E` from the
successfully pushed approved history, exactly as `R` is derived rather than
caller supplied.

A qualifying `E` MUST:

1. have exactly one parent `P`;
2. have `P == S` or have `S` as a first-parent ancestor of `P`;
3. add from an entirely absent canonical graph root exactly the complete path
   set for one graph;
4. change no path outside that one graph root;
5. add only regular mode-`100644` canonical blobs;
6. contain no readiness-record path change;
7. contain no unrelated, generated, cache, raw-data, outcome, credential, or
   operational artifact;
8. be reachable after a successful normal push from the freshly fetched
   approved branch history; and
9. precede the qualifying `R` on that same first-parent history.

`E` need not be the immediate parent of `R`. This permits the already-published
immutable graph to be reused by a later qualifying seal with the same
`evidence_preparation_identity`. Every commit between `E` and `R`, and every
commit between `R` and `H`, MUST leave this graph root tree byte-identical.

Commits between `S` and `E` are permitted only as ordinary first-parent
authority; they do not become evidence authority and MUST NOT touch the target
graph root. Existing current-readiness drift rules independently decide whether
such commits alter governed source authority.

A merge commit cannot be `E`. A graph introduced only through a non-first-parent
parent, an orphaned commit, a local-only commit, a tag, a separate ref, or an
unreachable Git object grants no authority.

## 9. Preservation of readiness seal R

`R` retains its frozen definition without exception:

- one parent;
- exactly the canonical readiness-record path changed relative to that parent;
- exact reviewed record bytes;
- `S` ancestry;
- approved first-parent history;
- pushed remote reachability; and
- no evidence path changed by `R`.

The complete graph MUST already exist byte-for-byte in `R`'s parent tree. `R`
does not publish, repair, copy, rename, delete, or select evidence. Its record
selects the graph only through the already-governed
`evidence_preparation_identity`.

The exact ancestry is:

```text
S first-parent-ancestor-of E
E first-parent-ancestor-of R
R first-parent-ancestor-of-or-equal-to H
```

`E`, `R`, and `H` never feed into an evidence identity or readiness identity.

## 10. Idempotency, collision, and mutation

The namespace is immutable and compare-only.

- If the canonical root is absent, one complete qualifying `E` may add it.
- If the complete canonical root already exists with identical bytes and a
  qualifying `E` is established in approved first-parent history, publication
  is an idempotent no-op and reuses that `E`.
- If identical or partial root bytes exist without a qualifying `E`,
  publication fails closed; it MUST NOT manufacture an empty commit or adopt
  unexplained paths.
- A no-change or empty commit is not a second `E`.
- If any target path exists with different bytes, mode, or object type,
  publication fails closed.
- If the root is partial, contains an extra file, or lacks graph closure,
  publication fails closed; it MUST NOT repair, complete, overwrite, or delete
  the root.
- Two different byte sequences may never claim the same identity-addressed
  path.
- Publishing the same graph under another experiment, aggregate identity,
  alias, or alternate root is not an authoritative substitute.

From `E` through `H`, no first-parent commit may alter, remove, rename, or
reintroduce any path below the selected root. Current readiness MUST scan that
history. Any later root change, including removal followed by byte-identical
reintroduction, makes the publication history ambiguous. Restoration does not
erase the intervening mutation.

Different complete graph roots for different aggregate identities may coexist.
They do not create ambiguity: the sealed record selects exactly one `A`.
Multiple readiness seals may lawfully bind the same immutable graph. They reuse
the original unique `E`; each seal remains a distinct `R` under existing
authority.

Concurrent publishers begin from the same fetched approved head. At most one
normal fast-forward push can establish the absent-to-complete transition. A
losing publisher MUST refetch: it reuses the newly authoritative `E` only when
the complete bytes are identical and every rule above passes; otherwise it
fails closed. Force-push, ref rewriting, and merge-based conflict resolution
are prohibited publication behavior.

## 11. Current-readiness retrieval

For one evaluation, current readiness MUST use one coherent fresh fetch and:

1. establish repository/ref authority and transient remote head `H`;
2. load the current canonical readiness-record blob from `H`;
3. canonically parse the record and reconstruct its readiness identity and
   source commit `S`;
4. derive the qualifying seal `R` under existing rules;
5. read `A = validation.evidence_preparation_identity` and derive the exact
   Section 3 graph root;
6. inspect the graph tree in `R`'s parent and derive the exact expected file
   set from `aggregate.json`;
7. traverse the approved first-parent history from `R`'s parent toward `S` to
   locate the unique commit that changed the root from absent to that exact
   complete tree;
8. require that commit to satisfy every Section 8 rule and designate it `E`;
9. inspect first-parent history from `E` exclusively through `H` and require
   no later change to the selected root;
10. load every graph blob through fetched Git object authority, never the
    working tree or an ambient cache;
11. validate canonical bytes, schemas, worker bundles, path identities, and
    exact graph closure;
12. independently reconstruct all first-order evidence using existing frozen
    reconstruction primitives; and
13. compare every reconstructed identity and direct value with the aggregate,
    sealed record, committed authority at `S`, and prospective registry before
    continuing current readiness.

Discovery may gather the fetched objects and history before their semantic
invariants become active. It MUST NOT mark an invariant passed early, classify
failure from exception text, or allow a later generic check to absorb an
earlier evidence owner.

No caller locator, working-tree file, local-only commit, alternate ref,
filesystem enumeration, `latest` selection, fallback vector, or scientific
rerun may supply evidence authority.

## 12. Independent evidence reconstruction

### 12.1 External-input evidence

For every nonzero input, current readiness loads and reconstructs the snapshot,
dataset-validation, and projection-evidence objects; reconciles declaration
order, member paths, order, counts, digests, member identities, parser/schema/
validator/projector components, dataset identity, projection identity, and
source authority; and compares them with the direct record and adapter at `S`.

Zero input requires all three aggregate vectors and all three object sets to be
exactly empty. The zero-input projection authority is independently derived
from the frozen material and is never loaded as an evidence file.

### 12.2 Replay and population

Current readiness loads replay-evidence-v2 and
population-accounting-evidence-v2 and independently reconstructs:

- scientific Replay identity;
- projection authority;
- candidate order;
- ordered source, Replay-unit, and decision identities;
- selector and Replay-preparer component authority;
- applicable Replay worker bundles;
- population dispositions, counts, reconciliation, and permitted reasons;
- zero-input empty Replay/population branches; and
- every aggregate and direct-record cross-binding.

Scientific Replay is not rerun. A fully rehashed replay-evidence substitution
or population-evidence substitution fails at `replay`.

### 12.3 Profile and artifacts

Current readiness loads and independently reconstructs profile-conformance and
artifact-declaration evidence, including the selected profile branch,
authorization-contract authority without outcomes, artifact declarations,
dependency order, and output-policy identity. Mismatches remain owned by
`outcome_policy` and `artifacts`, respectively.

### 12.4 Validation aggregate and workers

Current readiness loads readiness-test evidence, every worker bundle, and the
aggregate. It reconstructs readiness policy/results, normalized Phase-3A
output and worker authority, every ordinary worker command/capability/result,
the exact worker and semantic-component vectors, runtime/dependency/policy
bindings, every subordinate evidence vector, and the aggregate identity.

An internally rehashed but false worker, vector, readiness-test evidence, or
evidence-preparation aggregate fails at `validation`. The aggregate is never
accepted from hash shape, record equality, or empty fallback vectors.

## 13. Failure dispositions and invariant ownership

No new receipt class, disposition, invariant, or receipt schema is introduced.
Current-readiness receipts retain all existing contextual and known/absent
rules.

The exact new failure mapping is:

| Condition | Failed invariant | Disposition |
| --- | --- | --- |
| Approved remote cannot be freshly resolved or fetched | `git_authority` | `READINESS_UNRESOLVED_REMOTE` |
| Canonical record missing, malformed, noncanonical, or identity-invalid | `canonical_readiness_record` | `READINESS_INVALID_RECORD` |
| Required snapshot/dataset/projection file missing, corrupt, noncanonical, colliding, or false | `external_inputs` | `READINESS_INVALID_RECORD` |
| Required Replay or population file missing, corrupt, noncanonical, colliding, or false | `replay` | `READINESS_INVALID_RECORD` |
| Artifact evidence missing, corrupt, or false | `artifacts` | `READINESS_INVALID_RECORD` |
| Profile evidence missing, corrupt, or false | `outcome_policy` | `READINESS_INVALID_RECORD` |
| Readiness evidence, aggregate, worker bundle, graph closure, semantic-component vector, or worker vector missing, extra, corrupt, or false | `validation` | `READINESS_INVALID_RECORD` |
| Graph bytes are valid but no qualifying first-parent `E` precedes `R`, including local-only, after-R, merge, multi-path, non-first-parent, or orphan publication | `readiness_seal_and_ancestry` | `READINESS_ORPHANED` |
| More than one root-introduction transition exists, or the selected root changes after `E`, including removal/reintroduction | `readiness_seal_and_ancestry` | `READINESS_AMBIGUOUS` |
| Graph or evidence binds another `S` | earliest semantic owner of that object; aggregate/worker-only mismatch is `validation` | `READINESS_INVALID_RECORD` |
| Graph binds another adapter | earliest affected direct invariant; aggregate-only mismatch is `validation` | `READINESS_INVALID_RECORD` |
| Graph binds another profile | `outcome_policy`; aggregate-only mismatch after profile passes is `validation` | `READINESS_INVALID_RECORD` |
| Historical seal/evidence is claimed after a later canonical seal controls the current record | `readiness_seal_and_ancestry` | `SUPERSEDED` |

When the entire zero-input root is absent, the first required detached object
is Replay/population evidence, so `replay` owns the failure. For a nonzero
graph, missing input evidence is earlier and `external_inputs` owns it. An
aggregate-only absence or closure defect belongs to `validation`.

Valid graph bytes do not cure an invalid `E`; valid `E` history does not cure
invalid evidence. The earlier applicable invariant always wins. Ordinary
publication/retrieval failure produces a canonical `CURRENT_READINESS` receipt
when receipt construction remains possible. It does not broaden
`CANONICAL_RECEIPT_UNAVAILABLE`.

## 14. Ambiguity, reuse, and supersession

For the selected root, exactly one absent-to-complete root transition may occur
between `S` and `R`, and no later root transition may occur through `H`. That
transition is `E`.

- A second commit that does not change the root is not `E` and is ignored as
  evidence authority.
- A second root-changing commit makes the history `READINESS_AMBIGUOUS`, even
  if it restores identical bytes.
- A graph found only through a merge's non-first-parent history is orphaned.
- Additional complete roots for other aggregate identities are irrelevant.
- Reuse of one unchanged graph by multiple seals is permitted and retains the
  original `E`.
- The currently derived canonical record and most-recent qualifying `R`
  control current readiness. An older queried seal cannot regain authority
  because its graph remains reachable. Existing `SUPERSEDED` semantics apply.

Production APIs MUST NOT accept an operator-selected `E` or historical `R`.

## 15. Historical and prospective selection

This decision applies only to readiness validation performed under the
prospective v1.1 authority generation after this decision is frozen, committed,
pushed, and independently remote-backed.

A pre-decision `READINESS_VALIDATED` result is not grandfathered into
publication authority. Its exact candidate and complete retained evidence may
be published only after the current frozen Slice-4 evaluator re-establishes
`READINESS_VALIDATED` from those exact bytes and evidence without scientific
re-execution. If the complete evidence is unavailable, no publication is
authorized from hashes or reports alone.

This decision does not mutate, normalize, reinterpret, recompute, republish,
or relabel:

- historical Phase-2 authority;
- historical Phase-3A authority or path-bearing Phase-3A output;
- historical Phase-3B authority, evidence, aggregates, or workers;
- historical schemas, registries, readiness records, or checkpoints;
- adapter-v1 or adapter-v2 authority;
- frozen Slice 1, Slice 2, Slice 3, or Slice 4 implementation authority; or
- the frozen zero-input Phase-3B semantic model.

No historical evidence object receives an `E` retroactively.

## 16. Registry, schema, and identity impact

This decision creates no new execution-readiness semantic kind and changes no
registry membership. Counts remain:

```text
historical:  6 -> 10 -> 20
prospective: 6 -> 10 -> 20 -> 29
```

It requires:

- no readiness-record-v3;
- no evidence-preparation-v3;
- no new or revised evidence schema;
- no new evidence, aggregate, readiness, or worker identity domain;
- no 30th registry kind; and
- no simultaneous v1/v2 semantic-kind membership.

The worker publication bundle is a closed transport representation of already
governed worker identity and result material. It is not a semantic evidence
kind, is not registry-selected, and has no identity of its own. Its fixed
transport revision is selected by this prospective publication authority, not
by callers or filesystem discovery.

## 17. Information-flow and repository hygiene

The graph is evidence-authority metadata, not a research-data archive. It MUST
contain no:

- raw external-input contents;
- raw projected scientific payloads;
- outcomes, labels, winners, result values, or interpretations;
- ranking or evaluation output;
- `DecisionContext`, `FeatureContext`, or strategy-visible result state;
- credentials, tokens, private keys, secrets, or personal data;
- absolute, temporary, checkout, sandbox, controller, or machine-local paths;
- PIDs, timestamps, hostnames, nondeterministic diagnostics, logs, stdout, or
  stderr; or
- generated dependency roots, caches, wheel stores, datasets, or runtime
  artifacts.

Snapshot and projection evidence may contain governed byte counts, digests,
identities, relative semantic member paths, and schema/component authority. It
MUST NOT copy the corresponding payload bytes into Git.

All collection ordering comes from existing canonical evidence semantics, not
filesystem enumeration. Git object retrieval is read-only except for the
already-governed fetch/object-cache behavior of current readiness.

## 18. Identity DAG and cycle exclusion

The acyclic semantic authority is:

```text
S + committed prerequisite authority
  -> detached Phase-3B evidence objects
  -> subordinate evidence identities
  -> evidence-preparation-v2 aggregate
  -> evidence_preparation_identity A
  -> readiness-record-v2
  -> readiness_identity
  -> READINESS_VALIDATED

READINESS_VALIDATED + those already-fixed canonical evidence bytes
  -> publication commit E

canonical readiness-record bytes
  -> seal commit R

S -> E -> R -> H

H + R + sealed A
  -> canonical graph path
  -> E and graph bytes
  -> independent evidence reconstruction
  -> current-readiness result
```

`E`, `R`, and `H` do not enter evidence, aggregate, worker, or readiness
identity material. The graph does not bind readiness identity. The record
already binds the graph root, so a reverse readiness binding would create a
cycle and is prohibited. Repository/ref authority is established by Git
history and record context rather than duplicated into subordinate identities
whose frozen formulas do not contain it.

## 19. Side-effect and lifecycle boundary

After this decision is reviewed, frozen, committed, pushed, and independently
remote-backed, it authorizes only a future implementation that publishes the
already-validated canonical metadata graph in Git and retrieves it during
current readiness.

It does not authorize:

- rerunning Phase 3B or scientific Replay;
- rewriting or persisting a different candidate;
- changing schemas, specifications, or historical evidence;
- launch-authority or launch-input snapshots;
- launch validation, smoke, or a second fetch;
- control-storage contact or availability checks;
- allocation, ordinal consumption, or namespace realization;
- attempt identity, control record, or recovery creation;
- outcome authorization, ranking, evaluation, or experiment execution; or
- any Slice-6 capability.

`E` is the sole newly governed side effect. Creating `R` remains a separate
existing publication action, and current readiness remains scientifically
read-only.

## 20. Slice-5 resumption contract

Only after this decision becomes frozen and remote-backed may Slice 5 resume
to:

1. preserve its existing owner-level correction;
2. construct the canonical graph from the exact evidence already used for
   `READINESS_VALIDATED`;
3. publish that graph through the governed `E` mechanism;
4. retrieve it from one coherent fetched approved Git history;
5. independently reconstruct Phase-3B evidence during current readiness;
6. reject a rehashed Replay-evidence substitution at `replay`;
7. reject a rehashed population-evidence substitution at `replay`;
8. reject a rehashed evidence-preparation aggregate substitution at
   `validation`;
9. complete the ordered multi-member current-readiness fixture; and
10. complete Slice-5 adversarial verification.

This authorization does not extend to launch, Slice 6, or any later lifecycle
capability.

## 21. Comprehensive checkpoint

The comprehensive Execution Readiness checkpoint MUST NOT be created as part
of this decision. It becomes due only after:

1. Slice 5 is corrected;
2. detached evidence publication and retrieval are implemented;
3. Slice 5 passes adversarial review;
4. Slice 5 is frozen and committed;
5. Slice 5 is pushed; and
6. the remote HEAD is independently verified, completing the implementation
   boundary through `EXECUTION_READY`.

That future comprehensive checkpoint will supersede the current intermediate
checkpoint only as the active continuation checkpoint. Historical checkpoints
remain immutable.

## 22. Self-adversarial closure

The governed result for each adversarial case is:

| Case | Deterministic result |
| --- | --- |
| Missing graph object | Earliest object owner / `READINESS_INVALID_RECORD` |
| Missing entire zero-input graph | `replay` / `READINESS_INVALID_RECORD` |
| Missing entire nonzero graph | `external_inputs` / `READINESS_INVALID_RECORD` |
| Local-only or unpushed E with otherwise valid bytes | `readiness_seal_and_ancestry` / `READINESS_ORPHANED` |
| E after R | `readiness_seal_and_ancestry` / `READINESS_ORPHANED` |
| Merge or non-first-parent E | `readiness_seal_and_ancestry` / `READINESS_ORPHANED` |
| E changes an unrelated path | `readiness_seal_and_ancestry` / `READINESS_ORPHANED` |
| Partial graph | Earliest missing object owner; aggregate/closure-only defect is `validation` / `READINESS_INVALID_RECORD` |
| Extra graph file | `validation` / `READINESS_INVALID_RECORD` |
| Corrupt/noncanonical object | Its semantic owner / `READINESS_INVALID_RECORD` |
| Identity-addressed byte collision | Its semantic owner / `READINESS_INVALID_RECORD`; publication also fails closed |
| Internally rehashed false evidence | Its first-order semantic owner / `READINESS_INVALID_RECORD` |
| Wrong S, adapter, or profile | Earliest cross-binding owner fixed in Section 13 |
| Historical Phase-3A worker substituted prospectively | `validation` / `READINESS_INVALID_RECORD` |
| Zero graph carrying nonzero objects/workers | Earliest `external_inputs`, `replay`, or `validation` owner |
| Nonzero graph selecting zero branch | `external_inputs` or `replay` / `READINESS_INVALID_RECORD` |
| Duplicate no-change publication commit | Not E; original E remains authoritative |
| Root removal or reintroduction | `readiness_seal_and_ancestry` / `READINESS_AMBIGUOUS` |
| Two root-introduction transitions | `readiness_seal_and_ancestry` / `READINESS_AMBIGUOUS` |
| Old R after a later current seal | `readiness_seal_and_ancestry` / `SUPERSEDED` |
| Raw input, outcome, secret, or operational path in graph | Publication fails; if sealed, earliest object/closure owner / `READINESS_INVALID_RECORD` |
| Worker-vector reorder, duplicate, missing, or extra identity | `validation` / `READINESS_INVALID_RECORD` |
| E/R/H inserted into evidence identity material | Identity reconstruction fails at the affected owner |
| Registry adds a transport kind or count 30 | `schema_registry` / `READINESS_INVALID_RECORD` |

No case depends on commit messages, exception text, local filesystem order,
caller-selected authority, or ambient state.

## 23. Normative closure

This decision fixes exactly one canonical namespace, root path, subordinate
layout, worker-bundle representation, graph membership model, publication
commit shape, ancestry rule, idempotency rule, collision rule, retrieval
algorithm, failure mapping, historical boundary, and information-flow policy.

No normative choice within this decision's scope remains for implementation.
Implementation and adversarial verification remain future work; no `E`, `R`,
published graph, corrected Slice-5 result, or comprehensive checkpoint is
claimed to exist by this proposal.
