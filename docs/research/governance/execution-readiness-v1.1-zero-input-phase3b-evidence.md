# Execution Readiness v1.1 Zero-Input Phase-3B Evidence Decision

Status: Proposed for targeted adversarial review

## 1. Scope and authority

This decision resolves only the canonical prospective Phase-3B representation
for an adapter-declaration-v3 that declares exactly zero governed external
inputs. It is governed by:

- the [Execution Readiness v1.1 specification](../specifications/experiment-execution-readiness-v1.1.md);
- the [Execution Readiness clarification decision](execution-readiness-v1-clarification-decision.md);
- the [readiness-test-policy-v2 decision](execution-readiness-v1.1-readiness-test-policy-versioning.md);
- the [prerequisite-authority decision](execution-readiness-v1.1-prerequisite-authority-identities.md);
- the [readiness-record-v2 decision](execution-readiness-v1.1-readiness-record-v2.md); and
- the [Phase-3C intermediate checkpoint](../../project-checkpoints/ore-v3-execution-readiness-phase3c-intermediate.md).

Those authorities, frozen Slices 1 through 3, and every historical Phase-3B
schema and evidence object remain otherwise unchanged. This decision does not
authorize Phase-3C candidate persistence, seal `R`, current readiness,
`EXECUTION_READY`, launch, smoke execution, allocation, control records,
recovery, outcome authorization, ranking, evaluation, or experiment execution.

## 2. Governing zero-input predicate

The zero-input branch applies if and only if all of these facts reconstruct
from the same source commit `S`:

1. the explicitly selected prospective adapter revision is
   `adapter-declaration-v3`;
2. its closed `external_inputs.declarations` collection is exactly `[]`;
3. its closed `evidence_preparation.dataset_contracts` collection is exactly
   `[]`; and
4. the experiment identifier, profile identity, adapter identity, repository
   authority, and source commit all reconstruct under the existing prospective
   authority chain.

An empty declaration collection paired with a nonempty dataset-contract
collection, or the inverse, is invalid. No orphan dataset contract can become
zero-input Replay authority. This predicate is reconstructed; it is never a
caller-selected mode.

The `external_inputs` readiness invariant remains applicable. Its direct
record fields are exactly:

```json
{
  "dataset_validation_evidence_identities": [],
  "declarations": [],
  "input_snapshot_identities": [],
  "projection_evidence_identities": []
}
```

Thus:

```text
prospective_phase3a_command_identity =
  SHA256(
    UTF8("orev3:phase3b-worker-evidence:v1\n")
    || canonical(prospective_phase3a_command_material)
  )
```

Absence, `null`, an omitted field, a placeholder declaration, or a synthetic
input is invalid.

## 3. Zero-input semantic model

Zero governed external inputs produce an explicit authority-only empty model:

- there is no immutable-input snapshot object;
- there is no dataset-validation evidence object;
- there is no outcome-blind projection evidence object;
- there is no projector worker;
- there is no Replay-preparation worker;
- the scientific Replay has zero source, Replay-unit, and decision identities;
- population accounting has zero source, included, and excluded units; and
- Replay selector and preparer implementations remain committed authority but
  are not invoked.

The empty Replay is not fabricated scientific data and is not an assertion
about an outcome. No sentinel source unit, placeholder disposition, fake
dataset, fake projection object, or synthetic scientific record is permitted.

## 4. Zero-input projection authority

### 4.1 Purpose and coordinates

The zero-input projection authority is a derived identity, not a projection
evidence object and not a new schema-registry kind. It proves that no
projection can or must exist because the selected adapter declares no external
inputs.

Its revision token is exactly:

```text
zero-input-projection-authority-v1
```

Its identity domain is exactly:

```text
orev3:experiment-zero-input-projection-authority:v1\n
```

### 4.2 Canonical identity material

The closed identity material contains exactly these fields:

1. `adapter_identity`;
2. `experiment_identifier`;
3. `external_input_count`;
4. `external_input_identities`;
5. `profile_identity`;
6. `projection_authority_revision`; and
7. `source_commit`.

Their required values are:

- `adapter_identity`: the independently reconstructed adapter-v3 identity;
- `experiment_identifier`: the normalized governed experiment identifier;
- `external_input_count`: integer `0`;
- `external_input_identities`: exact empty array `[]`;
- `profile_identity`: the independently reconstructed execution-profile
  identity;
- `projection_authority_revision`:
  `zero-input-projection-authority-v1`; and
- `source_commit`: the exact detached source commit `S`.

The identity is:

```text
zero_input_projection_identity =
  SHA256(
    UTF8("orev3:experiment-zero-input-projection-authority:v1\n")
    || canonical(zero_input_projection_material)
  )
```

Canonical JSON uses the already-governed canonical encoder. Repository
authority and approved-ref authority independently establish `S`; they are not
duplicated inside this identity material. Adapter and profile identities bind
their complete committed authority. The domain is distinct from every real
projection and projection-evidence domain, so this identity cannot be confused
with a projection derived from input bytes.

### 4.3 Uses

The derived identity is used exactly as:

- readiness-record-v2 `replay.projection_identity`;
- prospective replay-evidence-v2 `projection_identity` in its zero-input
  branch; and
- the input to zero-input Replay scientific identity reconstruction.

It is not included in `external_inputs.projection_evidence_identities`, is not
represented by a detached projection-evidence object, and is not a worker
input capability because no Replay worker executes.

## 5. Zero-input Replay

The zero-input Replay core contains exactly the existing Replay fields with
these governed values:

- `candidate_order = []`;
- `decision_selection_identity` equals the adapter-v3
  `evidence_preparation.decision_selection.configuration_identity`;
- `ordered_decision_identities = []`;
- `ordered_replay_unit_identities = []`;
- `ordered_source_unit_identities = []`;
- `projection_identity` equals the reconstructed
  `zero_input_projection_identity`;
- `replay_preparer_component_identity` equals the committed component binding
  for `canonical-replay-preparer-v1` at `S`; and
- `selector_component_identity` equals the committed component binding for
  `latest-eligible-observation-selector-v1` at `S`.

Candidate order is canonically empty because no dataset contract or scientific
source exists from which a candidate population could be derived. There is no
separate candidate-order identity and no fallback to protocol text, ambient
configuration, or an orphan dataset contract.

The scientific Replay identity retains the existing domain:

```text
orev3:experiment-replay-evidence:v1\n
```

It is derived over the closed Replay core above, excluding both
`replay_identity` and `replay_evidence_identity`, by the existing canonical
identity function. The reuse of the domain preserves the semantic Replay kind;
the domain-separated zero-input projection identity makes the empty Replay
unambiguous and context-bound.

The prospective Replay evidence material adds exactly:

- `replay_identity` equal to the reconstructed scientific Replay identity; and
- `schema_version = 2`.

`replay_evidence_identity` uses the existing Replay evidence domain over that
complete material excluding only `replay_evidence_identity`.

No Replay selector or preparer worker executes. Independent validation
reconstructs the empty core and the two committed component identities at `S`.

## 6. Zero-input population accounting

The zero-input population evidence material contains exactly:

```json
{
  "dispositions": [],
  "excluded_count": 0,
  "included_count": 0,
  "permitted_exclusion_reasons": [],
  "schema_version": 2,
  "source_count": 0
}
```

`permitted_exclusion_reasons` is empty because no source unit can receive a
disposition. The adapter-v3 zero-input branch MUST also require its
`decision_selection.permitted_exclusion_reasons` collection to be exactly
empty. A nonempty exclusion vocabulary in a zero-input adapter is invalid;
this avoids unused caller-selected policy material changing the aggregate and
readiness identities.

There is no status, reason, disposition, source identity, Replay-unit identity,
decision identity, or sentinel in the zero-input branch.

The population evidence identity retains the existing domain:

```text
orev3:experiment-population-accounting-evidence:v1\n
```

It is derived over the complete material above, excluding only
`population_accounting_evidence_identity`.

## 7. Prospective replay-evidence-v2 schema

Freeze these coordinates:

- Semantic kind: `replay-evidence`
- Registry identifier: `replay-evidence-v2`
- `$id`: `orev3://schemas/execution-readiness/v1/replay-evidence-v2`
- Path: `src/orev3/execution/schemas/v1/replay-evidence-v2.schema.json`
- Title: `ReplayEvidenceV2`
- Schema version: `2`

The schema has exactly two closed branches:

1. a nonzero branch preserving every replay-evidence-v1 semantic constraint,
   requiring nonempty candidate and source collections and
   `schema_version = 2`; and
2. the zero-input branch from Section 5, requiring empty candidate, source,
   Replay-unit, and decision collections and `schema_version = 2`.

Both branches retain every existing identity and component field. The zero
branch is selected only after the predicate in Section 2 reconstructs. Schema
shape alone cannot authorize the branch.

Historical replay-evidence-v1 remains byte-identical and continues requiring
its historical nonempty representation.

## 8. Prospective population-accounting-evidence-v2 schema

Freeze these coordinates:

- Semantic kind: `population-accounting-evidence`
- Registry identifier: `population-accounting-evidence-v2`
- `$id`:
  `orev3://schemas/execution-readiness/v1/population-accounting-evidence-v2`
- Path:
  `src/orev3/execution/schemas/v1/population-accounting-evidence-v2.schema.json`
- Title: `PopulationAccountingEvidenceV2`
- Schema version: `2`

The schema has exactly two closed branches:

1. a nonzero branch preserving the complete v1 disposition semantics,
   requiring at least one source/disposition and `schema_version = 2`; and
2. the exact zero-input material in Section 6.

The zero branch cannot carry a disposition, reason, or sentinel. The nonzero
branch cannot use zero counts to enter the zero branch. Historical
population-accounting-evidence-v1 remains byte-identical.

## 9. Prospective evidence-preparation-v2 schema

Freeze these coordinates:

- Semantic kind: `evidence-preparation`
- Registry identifier: `evidence-preparation-v2`
- `$id`: `orev3://schemas/execution-readiness/v1/evidence-preparation-v2`
- Path: `src/orev3/execution/schemas/v1/evidence-preparation-v2.schema.json`
- Title: `EvidencePreparationV2`
- Schema version: `2`

The schema has exactly two closed branches.

The nonzero branch preserves all evidence-preparation-v1 authority, requires
nonempty snapshot, dataset, and projection collections, requires at least
seven semantic-component identities, requires the governed nonzero worker
set, and fixes `schema_version = 2`.

The zero-input branch fixes:

- `input_snapshot_identities = []`;
- `dataset_evidence_identities = []`;
- `projection_evidence_identities = []`;
- exactly four `semantic_component_identities`;
- exactly four `worker_evidence_identities`; and
- `schema_version = 2`.

The remaining required scalar identities retain their existing fields and
meaning. Python reconstruction MUST prove exact branch membership and exact
component/worker identity equality, including the normalized prospective
Phase-3A worker authority in Section 11; array cardinality alone never
establishes authority. Historical evidence-preparation-v1 remains
byte-identical.

## 10. Semantic-component authority

`semantic_component_identities` means the sorted unique identities of every
governed semantic component whose authority directly contributes to the
prepared evidence, whether invoked in a capability worker or applied as a
pure controller validation. It is not the complete repository policy inventory
and its cardinality is not a proxy for input count.

The zero-input vector contains exactly these four reconstructed bindings:

1. `canonical-replay-preparer-v1` — authority-bound only; supplies the Replay
   construction contract but is not invoked;
2. `latest-eligible-observation-selector-v1` — authority-bound only; supplies
   the selector contract but is not invoked;
3. `static-profile-validator-v1` — invoked as the controller-pure profile
   validation authority; and
4. `static-artifact-validator-v1` — invoked as the controller-pure artifact
   validation authority.

Each identity is reconstructed from the finite component policy and exact
committed identifier, revision, path, Git object, SHA-256, and worker kind at
`S`. The vector is sorted lexically by lowercase identity value and is unique.

Raw parser, projector, and dataset-validator component identities are
prohibited because no declaration selects them and no corresponding semantic
operation occurs.

## 11. Worker authority

### 11.1 Historical and prospective reconstruction

Historical Phase-3A and Phase-3B evidence continues to reconstruct its
Phase-3A worker exactly as originally frozen. In particular, its output
identity remains the hash of its historical result material, including the
historical physical `closed_dependency_root_path` field where that field was
present. Historical output identities, worker identities, aggregate
identities, and their domains are immutable. They are not normalized,
recomputed, upgraded, or relabeled.

Fresh prospective v1.1 Phase-3B evidence MUST instead use the normalized
Phase-3A output and worker reconstruction in this section. Selection is fixed
by the already-governed authority-generation value
`prospective-v1.1-phase3a`; it is not a caller option. Historical generation
selects only historical reconstruction, and prospective generation selects
only normalized reconstruction. There is no `latest`, discovery, fallback,
or acceptance of the other generation's identity.

### 11.2 Normalized Phase-3A output authority

The prospective normalized Phase-3A output identity proves the semantic
authority established by the `PHASE3A_VALIDATOR` `validate_runtime` sibling.
It binds the detached repository, adapter, runtime, closed dependency content,
complete source scopes, and committed validation code without binding where a
controller happened to materialize the closed dependency root.

Its revision token is exactly:

```text
phase3a-normalized-output-v1
```

The closed canonical material contains exactly these fields:

1. `adapter_identity`;
2. `adapter_registry_identity`;
3. `approved_branch_ref`;
4. `authority_generation`;
5. `closed_dependency_environment_identity`;
6. `command`;
7. `dependency_import_origins`;
8. `evidence_disposition`;
9. `network_denial_verified`;
10. `normalized_output_revision`;
11. `remaining_predicates`;
12. `repository_authority_identifier`;
13. `runtime_contract_identity`;
14. `source_commit`;
15. `source_scopes`;
16. `status`; and
17. `worker_code_git_identities`.

Their values and canonical collection rules are fixed as follows:

- `adapter_identity` and `adapter_registry_identity` equal the independently
  reconstructed prospective adapter-v3 and committed registry identities at
  `S`;
- `approved_branch_ref` and `repository_authority_identifier` equal the
  committed repository authority used to establish `S`;
- `authority_generation` is exactly `prospective-v1.1-phase3a`;
- `closed_dependency_environment_identity` is the existing content-derived
  closed-dependency identity reconstructed from the sorted distributions,
  projected wheel artifacts, and complete relative-path/file digest vector;
- `command` is exactly `validate_runtime`;
- `dependency_import_origins` is the exact ordered vector of normalized
  dependency-root-relative POSIX paths produced by the runtime contract's
  `dependency_import_probes`, in probe declaration order. Its length equals
  the probe count, and each path is independently proven to be contained in
  the content-derived closed dependency root;
- `evidence_disposition` is exactly
  `PREPARATION_ENVIRONMENT_EVIDENCE_PASSED`;
- `network_denial_verified` is exactly `true`;
- `normalized_output_revision` is exactly
  `phase3a-normalized-output-v1`;
- `remaining_predicates` is exactly this ordered vector:
  `artifact_declaration_validation`,
  `candidate_readiness_record_generation`,
  `external_input_snapshot_validation`,
  `mandatory_readiness_test_execution`, `population_accounting`,
  `profile_operational_validation`, `readiness_seal_and_current_status`, and
  `replay_reconstruction`;
- `runtime_contract_identity` is independently reconstructed from the
  committed runtime contract at `S`;
- `source_commit` is exactly `S`;
- `source_scopes` is the complete reconstructed Phase-3A prerequisite scope
  vector. Each item has the existing closed source-scope shape, the vector is
  ordered by `repository_path` and then `role`, paths are unique, and every
  Git mode/object/nesting/parent relationship reconstructs at `S`; and
- `worker_code_git_identities` is the sorted unique lowercase Git-object
  identity vector for exactly these committed validation modules:
  `src/orev3/execution/canonical.py`,
  `src/orev3/execution/git_state.py`,
  `src/orev3/execution/preparation.py`,
  `src/orev3/execution/preparation_worker.py`,
  `src/orev3/execution/readiness_record.py`,
  `src/orev3/execution/registry.py`, and
  `src/orev3/execution/runtime.py`; and
- `status` is exactly `evidence_passed`.

The runtime contract is the existing aggregate authority for its dependency
lock identity and committed lock bytes, offline-artifact-manifest identity and
committed manifest bytes, runtime-bundle identity, host-system identity, and
allowed execution/runtime policy. Those identities are reconstructed from the
runtime contract and its referenced committed objects and MUST agree with the
closed dependency environment. They are not duplicated as independently
selectable fields in the normalized output material. A change to the lock,
manifest, runtime bundle, host authority, or closed projected wheel content
therefore changes the runtime-contract or closed-environment identity, or
fails reconstruction.

The normalized output identity retains the existing generic worker-evidence
identity domain:

```text
orev3:phase3b-worker-evidence:v1\n
```

and is derived as:

```text
normalized_phase3a_output_identity =
  SHA256(
    UTF8("orev3:phase3b-worker-evidence:v1\n")
    || canonical(normalized_phase3a_output_material)
  )
```

Retaining the domain is safe because the semantic object remains a worker
output authority and the mandatory revision and authority-generation fields
make the prospective closed material disjoint from the historical path-bearing
material. A new domain solely for normalization is therefore prohibited.

### 11.3 Operational-path exclusion

No prospective normalized output, command, worker, aggregate, or readiness
identity material may contain or derive from:

- `closed_dependency_root_path` as a physical filesystem path;
- a controller working directory or temporary directory;
- a sandbox path, checkout-local absolute path, or machine-local locator;
- a process identifier, timestamp, hostname, or hostname-specific temporary
  location; or
- any equivalent execution-local locator state.

These values may be used transiently to execute and validate the worker, but
they MUST be discarded before normalized material is constructed. Relative
repository paths inside the governed source-scope and committed-code vectors
are semantic repository authority and are not prohibited operational
locators.

### 11.4 Prospective Phase-3A worker identity

The prospective command identity uses the retained generic worker-evidence
domain over exactly this closed material:

```json
{
  "authority_generation": "prospective-v1.1-phase3a",
  "command": "validate_runtime",
  "invocation_identifier": "phase3a-validate-runtime",
  "worker_kind": "PHASE3A_VALIDATOR",
  "worker_revision": "phase3a-normalized-worker-v1"
}
```

The prospective Phase-3A worker revision is exactly
`phase3a-normalized-worker-v1`. Its closed worker identity material contains
exactly:

1. `capability_policy_identity`;
2. `closed_dependency_identity`;
3. `code_capability_git_identities`;
4. `command_identity`;
5. `input_capability_identities`;
6. `invocation_identifier`;
7. `output_identity`;
8. `runtime_contract_identity`;
9. `sandbox_template_identity`;
10. `source_commit`;
11. `successful_worker_disposition`;
12. `worker_kind`;
13. `worker_module_git_identity`; and
14. `worker_revision`.

The required values are:

- `capability_policy_identity` equals the selected prospective evidence-
  preparation capability policy identity;
- `closed_dependency_identity` equals the normalized output's reconstructed
  `closed_dependency_environment_identity`;
- `code_capability_git_identities` equals the exact Section 11.2 committed-code
  vector;
- `command_identity` equals independent reconstruction of the command material
  above;
- `input_capability_identities = []` exactly;
- `invocation_identifier = "phase3a-validate-runtime"` exactly;
- `output_identity` equals the reconstructed
  `normalized_phase3a_output_identity`, never the historical raw-result
  identity;
- `runtime_contract_identity` and `source_commit` equal the normalized output
  and independently reconstructed prospective authority;
- `sandbox_template_identity` equals the fixed committed
  Phase-3A network-sandbox template identity selected by the capability
  policy;
- `successful_worker_disposition = "evidence_passed"` exactly;
- `worker_kind = "PHASE3A_VALIDATOR"` exactly;
- `worker_module_git_identity` equals the Git object identity of
  `src/orev3/execution/preparation_worker.py` at `S`; and
- `worker_revision = "phase3a-normalized-worker-v1"` exactly.

The worker identity retains the existing generic worker-evidence domain and is
derived exactly as:

```text
prospective_phase3a_worker_identity =
  SHA256(
    UTF8("orev3:phase3b-worker-evidence:v1\n")
    || canonical(prospective_phase3a_worker_material)
  )
```

Retention is safe and required: the semantic object remains worker evidence,
while the mandatory revision, invocation, code-capability, and normalized-
output fields make its prospective representation disjoint from historical
worker material. The prospective validator MUST reject a historical worker
identity even if every unchanged field agrees, and the historical loader MUST
reject or never select the prospective form.

### 11.5 Exact zero-input worker vector

The zero-input Phase-3B aggregate contains exactly these four independently
reconstructed worker identities:

1. the prospective normalized `PHASE3A_VALIDATOR` worker defined above;
2. the `READINESS_TEST` `collect` worker with invocation `collection-a`;
3. the `READINESS_TEST` `collect` worker with invocation `collection-b`; and
4. the `READINESS_TEST` `run_exact` worker with invocation `execution`.

This list defines membership, not serialized position. The canonical aggregate
vector is the sorted unique lowercase identity vector of exactly those four
members. Reordering, omission, duplication, or substitution rejects.

The profile validator and artifact validator are controller-pure semantic
components and do not produce worker evidence. Replay selector and preparer
authority remains in `semantic_component_identities`, but they produce no
worker evidence because no Replay worker executes. No parser, dataset-
validator, projector, `INPUT_PROJECTOR`, or `REPLAY_PREPARATION` worker exists
for zero inputs, and no empty capability or placeholder worker is fabricated.

### 11.6 Nonzero prospective evidence

The same normalized Phase-3A output and worker reconstruction is mandatory for
fresh nonzero-input prospective v1.1 evidence-preparation-v2. Its complete
worker set otherwise remains governed by its real input declarations and
executions; this decision does not impose a fixed nonzero cardinality.

Every other prospective worker output already uses the generic worker runner's
canonical JSON result identity and closed worker material. Operational source,
dependency, request, temporary, and output paths are used by the controller
but are not returned in those governed worker results or worker identity
material. No additional concrete machine-local path defect is identified, so
this decision does not revise their semantics. If such a field is encountered,
prospective evidence MUST fail closed; it cannot be normalized by analogy
without frozen authority.

## 12. Zero-input Phase-3B aggregate

The zero-input evidence-preparation-v2 aggregate contains the existing closed
field set with:

- `source_commit`: exact `S`;
- `runtime_contract_identity`: independently reconstructed runtime authority;
- `dependency_environment_identity`: independently reconstructed detached
  environment authority;
- `adapter_identity`: the selected zero-input adapter-v3 identity;
- `readiness_test_evidence_identity`: the governed passing readiness-test
  evidence identity;
- `input_snapshot_identities = []`;
- `dataset_evidence_identities = []`;
- `projection_evidence_identities = []`;
- `replay_evidence_identity`: the reconstructed zero-input Replay-evidence-v2
  identity;
- `population_evidence_identity`: the reconstructed zero-input
  population-accounting-evidence-v2 identity;
- `profile_evidence_identity`: the reconstructed prospective profile evidence
  identity;
- `artifact_evidence_identity`: the reconstructed artifact evidence identity;
- `capability_policy_identity`: the selected evidence-preparation policy
  identity;
- `semantic_component_identities`: the exact Section 10 vector;
- `worker_evidence_identities`: the exact Section 11 vector; and
- `schema_version = 2`.

The Phase-3A member of `worker_evidence_identities` is always the Section 11
prospective normalized worker identity for both zero-input and nonzero-input
v2 aggregates. The historical path-bearing Phase-3A worker identity is invalid
in evidence-preparation-v2. Conversely, evidence-preparation-v1 retains its
historical worker rules and cannot select the normalized identity.

Because operational paths occur in none of the normalized materials, the same
governed authority under different controller temporary roots or checkout
locations produces the same normalized output identity, Phase-3A worker
identity, worker vector, evidence-preparation identity, and readiness identity.
A change to governed source, runtime, dependency, policy, scope, or committed
worker authority changes the first identity that binds it or fails independent
reconstruction; downstream rehashing cannot establish substituted authority.

Every collection uses its existing canonical ordering. The aggregate identity
retains the existing domain:

```text
orev3:experiment-evidence-preparation:v1\n
```

It is reconstructed over all aggregate material except
`evidence_preparation_identity`. Schema version 2 and the exact empty/vector
material distinguish it from historical aggregate evidence without changing
the semantic object kind.

## 13. Readiness-record-v2 compatibility

The existing readiness-record-v2 schema remains unchanged. Its current fields
truthfully represent this model:

- the four external-input collections are empty;
- Replay candidate/source/Replay-unit/decision collections are empty;
- `replay.projection_identity` carries the derived Section 4 identity;
- Replay and population evidence identities select the prospective v2
  objects;
- population counts are zero and dispositions are empty;
- selector and preparer component identities remain exact committed
  authority; and
- `validation.evidence_preparation_identity` binds the v2 aggregate.

Direct record material and detached evidence MUST reconstruct independently and
compare equal. The record does not embed the zero-input projection material;
the validator reconstructs it from adapter, experiment, profile, and `S`.

No additional schema revision or semantic kind is required for normalized
Phase-3A worker authority. Evidence-preparation-v2 already carries worker
identities as exact SHA-256 identity values; normalization changes their
prospective reconstruction semantics, not the aggregate field shape. The only
prospective schema revisions remain replay-evidence-v2,
population-accounting-evidence-v2, and evidence-preparation-v2.

## 14. Registry overlays and counts

Historical Phase 3B continues to select:

- `replay-evidence-v1`;
- `population-accounting-evidence-v1`; and
- `evidence-preparation-v1`.

Fresh prospective v1.1 Phase 3B and the prospective final readiness registry
select:

- `replay-evidence-v2`;
- `population-accounting-evidence-v2`; and
- `evidence-preparation-v2`.

The prospective revisions apply to both zero-input and nonzero-input fresh
prospective evidence. Nonzero evidence uses the closed nonzero v2 branches and
is reconstructed with `schema_version = 2`; it is not relabeled historical
evidence.

Selection is explicit by registry map. Filesystem enumeration, `latest`,
fallback, caller selection, and simultaneous v1/v2 membership are prohibited.
Each selected registry contains exactly one revision of each semantic kind.

Semantic-kind counts remain:

```text
Historical Phase 2: 6
Historical Phase 3A: 10
Historical Phase 3B: 20

Prospective Phase 2: 6
Prospective Phase 3A: 10
Prospective Phase 3B: 20
Prospective final v1.1: 29
```

The three schema revisions are substitutions, not new semantic kinds. No 30th
kind or second aggregate registry identity is introduced.

## 15. Historical preservation

The following remain immutable and retain their historical coordinates,
bytes, digests, identity domains, registry selection, and evidence semantics:

- `evidence-preparation-v1`;
- `replay-evidence-v1`;
- `population-accounting-evidence-v1`;
- the historical Phase-3B 20-member registry;
- all historical Phase-3B evidence and workers;
- adapter-declaration-v1 and its evidence;
- frozen adapter-declaration-v2 and its evidence; and
- every frozen Slice-3 source commit and previously produced evidence object.

No historical evidence is recomputed, repaired, reinterpreted, upgraded, or
relabeled. The new files may coexist in the repository but are selected only
by the explicit prospective overlays.

## 16. Identity domains and dependency order

This decision introduces exactly one new identity domain: the zero-input
projection-authority domain in Section 4. It is necessary because that value is
not a real projection or projection-evidence identity. The normalized
Phase-3A output, command, and worker identities retain the generic worker-
evidence domain; their mandatory revision and authority-generation fields
separate their prospective material from historical material.

These existing domains are retained:

- scientific Replay and Replay evidence:
  `orev3:experiment-replay-evidence:v1\n`;
- population evidence:
  `orev3:experiment-population-accounting-evidence:v1\n`; and
- aggregate evidence:
  `orev3:experiment-evidence-preparation:v1\n`.

The acyclic dependency order is:

```text
repository authority + S
  -> zero-input adapter-v3 + experiment + profile identities
  -> zero-input projection authority
  -> committed selector/preparer component identities
  -> empty scientific Replay identity
  -> Replay-evidence-v2 identity
  -> empty population-accounting-evidence-v2 identity

repository authority + S
  -> runtime/dependency authority
  -> normalized Phase-3A output authority
  -> normalized Phase-3A worker identity
  -> readiness-test, profile, artifact, and worker evidence

all preceding Phase-3B authority
  -> evidence-preparation-v2 aggregate identity
  -> readiness-record-v2 direct material
  -> readiness_identity
```

No subordinate object depends on aggregate or readiness identity before that
identity is derived. The zero-input projection identity does not depend on
Replay, population, aggregate, or readiness identity.

## 17. Validation and failure ownership

Prospective validation MUST:

1. reconstruct the Section 2 predicate;
2. require the four direct external-input collections to be empty;
3. reject every snapshot, dataset, projection, projector worker, Replay worker,
   orphan dataset contract, or input component identity;
4. reconstruct the zero-input projection identity;
5. reconstruct empty Replay and population evidence under their v2 schemas;
6. reconstruct the exact semantic-component and worker vectors;
7. reconstruct the v2 aggregate; and
8. compare every direct readiness-record field and detached identity.

Wrong external-input emptiness fails `external_inputs`. Wrong zero-input Replay
or population authority fails `replay`. Wrong aggregate, readiness-worker,
runtime, or evidence-policy authority fails `validation`. Final canonical
record encoding and readiness identity remain owned by
`canonical_readiness_record`.

Rehashing downstream evidence does not move first-order failure ownership.

## 18. Information-flow and lifecycle boundary

The zero-input representation contains no outcome, label, winner, result
value, interpretation, ranking, evaluation output, DecisionContext,
FeatureContext, or strategy-visible outcome state. Empty Replay authority
proves only that no governed scientific input population exists for this
adapter at `S`.

Phase-3C external-input, Replay, outcome-policy, validation, and canonical
record invariants remain applicable. A fully conformant zero-input candidate
may produce `READINESS_VALIDATED`. This grants no persistence, current
readiness, launch, allocation, or scientific execution authority.

## 19. Implementation consequences

After this decision is reviewed and frozen, the smallest expected changes are:

New schemas:

- `src/orev3/execution/schemas/v1/replay-evidence-v2.schema.json`;
- `src/orev3/execution/schemas/v1/population-accounting-evidence-v2.schema.json`;
- `src/orev3/execution/schemas/v1/evidence-preparation-v2.schema.json`.

Narrow prospective implementation changes:

- `src/orev3/execution/readiness_record.py` for explicit overlays;
- `src/orev3/execution/evidence_preparation.py` for v2 aggregate material;
- `src/orev3/execution/evidence_preparation_worker.py` for the zero-input
  branch, absent projector/Replay workers, and normalized Phase-3A output and
  worker identity reconstruction;
- `src/orev3/execution/preparation.py` only to expose the deterministic
  prospective semantic result material separately from the operational closed
  dependency root locator;
- `src/orev3/execution/replay_preparation.py` for pure empty Replay/population
  reconstruction;
- `src/orev3/execution/git_state.py` for independent v2 reconstruction;
- `src/orev3/execution/readiness_candidate.py` only to consume the shared
  reconstruction at existing invariant owners; and
- focused Phase-3B, schema-registry, Slice-3, and complete Slice-4 zero-input
  tests.

Historical loaders and workers remain unchanged. No configuration or existing
schema is modified in place.

## 20. Self-adversarial convergence

The following substitutions have one deterministic rejection:

- one input under the zero branch: reject at branch reconstruction;
- zero inputs under a nonzero branch: reject;
- historical v1 schema selected prospectively: reject registry selection;
- fake projection evidence or dataset: reject external-input membership;
- synthetic source unit or disposition: reject the exact empty branch;
- zero-input projection identity from another experiment, adapter, profile, or
  source commit: reject identity reconstruction;
- nonempty candidate order: reject zero Replay material;
- parser/projector/dataset-validator semantic component: reject the exact
  four-component vector;
- projector or Replay worker: reject the exact worker-kind/invocation set;
- identical authority under different controller temporary roots or checkout
  paths: derive identical normalized Phase-3A output, worker, aggregate, and
  readiness identities;
- changed dependency lock, offline manifest, closed environment, runtime
  contract, runtime bundle, host authority, source scope, worker source, or
  source commit: change the applicable normalized identity or reject its
  reconstruction;
- historical Phase-3A worker selected prospectively, or normalized worker
  selected historically: reject explicit generation/revision selection;
- reordered or duplicate four-worker vector: reject exact sorted-unique
  membership;
- arbitrary normalized output with worker and aggregate rehashed: reject
  independent reconstruction from repository/runtime/source authority;
- rehashed aggregate with substituted subordinate authority: reject
  independent first-order reconstruction;
- v1/v2 dual registry membership or a 30th kind: reject registry cardinality;
- historical evidence relabeled v2: reject schema version and original-source
  selection;
- identity cycle: absent under Section 16's dependency order; and
- outcome-bearing extension: reject closed schemas and information-flow
  validation.

One-input and larger nonzero profiles use only the v2 nonzero branches and
retain real snapshot, dataset, projection, Replay-worker, population, and
component authority. Zero and nonzero representations cannot validate under
the same branch.

## 21. Normative closure

No normative choice remains for zero-input prospective Phase-3B evidence or
prospective Phase-3A worker normalization. Implementations do not choose a
Replay source, projection token, candidate order, population sentinel,
component inventory, worker invocation, output material, worker material,
revision, schema revision, registry overlay, or identity domain. All are fixed
above.
