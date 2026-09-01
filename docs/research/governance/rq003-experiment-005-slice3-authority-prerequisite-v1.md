# RQ-003 Experiment 005 Slice-3 Authority Prerequisite v1

- State: Adopted and frozen prospectively
- Experiment: `rq003-experiment-005-signed-share-imbalance-predictive-evaluation`
- Decision revision: `rq003-experiment-005-slice3-authority-prerequisite-v1`
- Scope: prospective Slice-3 authority choices only
- Readiness/adapter disposition: NARROW READINESS/ADAPTER REVISION REQUIRED
- Outcome-gate disposition: SUBORDINATE OUTCOME-GATE PROVENANCE INTERFACE REQUIRED

## 1. Purpose and controlling authority

This decision prospectively freezes the authority choices that must be adopted
before a separate writer may construct the Experiment 005 Slice-3 adapter,
configuration, execution entry point, artifact schemas, profile contracts,
implementation binding, declarations, or registry entry. It is not itself an
adapter, implementation binding, execution configuration, artifact schema,
profile contract, Source S, readiness record, or execution authorization.

The following tracked authority remains controlling:

- the adopted Experiment 005 protocol at
  `docs/research/experiments/rq003-experiment-005-signed-share-imbalance-predictive-evaluation.md`,
  SHA-256
  `38afa9005bb43050d23e430335e11654c374d4e2d6f4a9f541782c005bffefdc`;
- the adopted Minimum-Effect clarification at
  `docs/research/governance/rq003-minimum-effect-scope-clarification-v1.md`,
  SHA-256
  `f736ac301a49be5acca58ef75f5130c1533328cf83cc359c9a69b596c53c2f4b`;
- the frozen source-processing prerequisite at
  `docs/research/governance/rq003-experiment-005-source-processing-prerequisite-v1.md`,
  SHA-256
  `d6d5d0fb3777cdb2a95e3bbff53b4815c574de68e31d4b5f7f1a0409580799a4`;
- Research Execution Specification v2 revision
  `rq003-research-execution-specification-v2`, document SHA-256
  `75597ab27d2d2867c68be886785c1884db83b9a26c0428c337ff23d218ef9497`;
- Execution Readiness v1.1 and the existing adapter-v3, registry,
  profile-contract, implementation-binding, artifact/output, Replay, and
  attempt-local outcome-authorization authority; and
- the frozen Experiment 005 source-processing implementation and its closed
  conformance surface.

No provision below changes scientific population, measurement, ranking,
missingness, comparator, fold, bootstrap, inference, disposition, or
confirmation semantics.

## 2. Exact identifiers fixed by this decision

The following identifiers are the only identifiers permitted for the
corresponding future Slice-3 objects:

| Object | Identifier |
| --- | --- |
| Experiment | `rq003-experiment-005-signed-share-imbalance-predictive-evaluation` |
| Adapter | `rq003-experiment-005-adapter-v3` |
| Ordered external input | `rq003-experiment-005-replay-source-v1` |
| Outcome-source contract external input | `rq003-experiment-005-replay-source-v1` |
| Configuration | `rq003-experiment-005-configuration-v1` |
| Configuration schema | `rq003-experiment-005-configuration-schema-v1` |
| Ranking artifact | `rq003-experiment-005-ranking-artifact-v1` |
| Evaluation artifact | `rq003-experiment-005-evaluation-report-v1` |
| Ranking schema | `rq003-experiment-005-ranking-artifact-schema-v1` |
| Evaluation schema | `rq003-experiment-005-evaluation-report-schema-v1` |

These strings are identifiers, not identities. Each identity must be
independently reconstructed under the domain and material prescribed below.
No alias, path-derived substitute, or opaque matching hash is permitted.

## 3. Ordered external-input manifest authority

### 3.1 Fixed source and membership rule

The future adapter-v3 declared external input
`rq003-experiment-005-replay-source-v1` has `input_kind` equal to
`ordered_file_collection`, dataset version `replay-dataset-v1`, and exactly one
ordered manifest. Member order zero is the lifecycle member whose persisted
SHA-256 is
`7680856bc6a01f9b69be0921d6e66b3f43d5241a38e63b37871b6925c1d59ba7`.
Its `logical_identifier` is exactly `lifecycle`, its `member_order` is exactly
`0`, and its `member_path` is exactly
`data/derived/replay_dataset_v1.jsonl`. That path is the existing canonical
`replay-dataset-v1` source path; no alias is permitted.

The remaining members are exactly the exhaustive set of immutable observation
source files referenced by those protocol-fixed lifecycle bytes. The set is
formed by resolving every lifecycle observation reference, taking the unique
referenced source-file coordinates, and including each referenced source file
once. It excludes every unreferenced observation file, every later collector
file, every C2 source, and every alternative lifecycle file. The Slice-3
writer has no discretion to add, omit, replace, or choose members.

For every observation member, `member_path` is exactly the raw
`ObservationReference.source_file` string after validating that the string is
already NFC. Validation does not change its code points. Prefixing, rebasing,
trimming, slash conversion, basename or stem rewriting, repository-local
remapping, case folding, and normalization other than the equality check
against NFC are prohibited. The unchanged string must also satisfy the
adapter-v3 canonical repository-path validator. Failure of NFC equality,
repository-path validation, or unique resolution is a hard stop for dataset
governance; it must not be repaired.

The observation `logical_identifier` derivation is exactly:

```text
utf8 = member_path encoded as strict UTF-8
digest = lowercase hexadecimal SHA-256(utf8), exactly 64 characters
logical_identifier = "observation." + digest
```

The full digest is used with no truncation. Implementations independently
verify the identifier by recomputing it from the unchanged `member_path`.
Because member paths are unique, any duplicate derived identifier or any
SHA-256 collision is a hard stop for dataset governance. No ordinal,
basename, stem, or caller-supplied identifier is accepted.

After the lifecycle member, observation members are ordered ascending by the
pair `(logical_identifier, member_path)` in Unicode code-point order. Each
value satisfies the existing adapter-v3 identifier/path grammar. The ordered
vector contains no duplicate path, logical identifier, member identity, or
member order.

Complete member bytes are authenticated. Observation outcome-bearing regions
remain semantically opaque before attempt-local outcome authorization. Every
member binds exactly:

- `logical_identifier`;
- `member_path`;
- `member_order`;
- `byte_count`;
- `sha256`; and
- `member_identity`.

The collection binds exactly:

- `aggregate_byte_count` as the integer sum of member byte counts;
- `manifest_revision`;
- `manifest_identity`; and
- `external_input_identity`.

Member, manifest, and external-input identities use, without alteration, the
existing adapter-v3 domains
`orev3:readiness-adapter-external-input-member:v1`,
`orev3:readiness-adapter-external-input-manifest:v1`, and
`orev3:readiness-adapter-external-input:v1`, respectively. Their canonical
materials and reconstruction order are exactly those accepted by current
adapter-v3 authority. Slice 3 must not create Experiment-specific substitutes.

Every lifecycle reference must resolve to exactly one authenticated
member/path/line coordinate. Any unresolved or ambiguous reference, or any
source bytes that admit more than one candidate source graph, is a hard stop
and requires prospective dataset governance. It may not be treated as an
exclusion, repaired heuristically, or resolved by implementation choice.

This decision does not claim that the observation-member bytes and digests
have already been materialized. The deterministic manifest must be
materialized read-only under this rule and independently reviewed before the
production descriptor is created. Failure to reconstruct one unique manifest
is a stop, not permission to select a dataset.

### 3.2 Outcome-source relationship

The outcome-source contract refers to the same combined external-input
identifier `rq003-experiment-005-replay-source-v1`. Slice 3 creates exactly one
Phase-3B external-input declaration: the ordered lifecycle/observation
collection in Section 3.1. It creates no second outcome external input.

The shared identifier does not collapse capability boundaries. Phase 3B
authenticates all persisted bytes while lifecycle and observation outcome
regions remain semantically sealed. The pre-outcome decoder, projector,
Replay preparer, controller, and ranking path cannot parse or expose those
regions. Only the evaluation environment, after ranking freeze and valid
attempt-local authorization binding the same external-input identity, may
open and parse the authorized outcome semantics. This relationship creates no
locator, opener, parser, provider, authorization, or outcome access.

## 4. Experiment configuration authority

### 4.1 Path, version, and closed object

The prospective canonical path is
`config/research/readiness/experiments/rq003-experiment-005-configuration-v1.json`.
It is one newline-terminated canonical JSON object with `schema_version` equal
to `1`, `configuration_identifier` equal to
`rq003-experiment-005-configuration-v1`, and no unknown or optional
properties. Every nested object is closed. The complete semantic object has
exactly these top-level properties:

1. `schema_version`;
2. `configuration_identifier`;
3. `protocol`;
4. `execution_profile`;
5. `source_processing`;
6. `dataset`;
7. `decision_selection`;
8. `candidate_order`;
9. `measurements`;
10. `feature_set`;
11. `procedures`;
12. `folds_and_controls`;
13. `metrics`;
14. `numeric_contract`;
15. `bootstrap`;
16. `dispositions`;
17. `confirmation`;
18. `artifacts`; and
19. `configuration_identity`.

The property set of each nested object is also closed. The exact property
names are:

| Object | Exact properties |
| --- | --- |
| `protocol` | `experiment_identifier`, `protocol_revision`, `protocol_sha256`, `minimum_effect_identifier`, `minimum_effect_sha256`, `source_convention_revision` |
| `execution_profile` | `execution_profile`, `research_specification_profile_identity`, `adapter_profile_contract_identity` |
| `source_processing` | `configuration_path`, `configuration_git_blob_identity`, `configuration_byte_count`, `configuration_sha256`, `decoder_configuration_identity`, `projection_schema_path`, `projection_schema_identity`, `source_processing_prerequisite_identifier`, `source_processing_prerequisite_sha256` |
| `dataset` | `dataset_version`, `lifecycle_persisted_sha256`, `external_input_identifier`, `external_input_manifest_identity`, `homogeneous_source_protocol_revision` |
| `decision_selection` | `decision_selection_identifier`, `decision_selection_identity`, `boundary`, `chronology`, `equal_rpc_tie_order`, `governed_exclusion_rules` |
| `measurements` | `fundamental_measurement_pipeline_identity`, `share_imbalance_definition_identity`, `deployment_per_miner_definition_identity`, `deployed_lamport_vector_identity_domain`, `miner_count_vector_identity_domain` |
| `feature_set` | `feature_set_identity`, `ordered_fields` |
| each `procedures` entry | `name`, `role`, `rule`, `procedure_identity`, `tie_identity` |
| `folds_and_controls` | `fold_count`, `fold_order`, `adequate_support_per_fold`, `adequacy_rule_identity`, `comparability_identity_domain`, `control_family_semantics`, `sensitivity_semantics` |
| `metrics` | `reciprocal_rank_metric_identities`, `paired_vector_identities`, `primary_metric_identities`, `incremental_metric_identities`, `secondary_metric_identities` |
| `numeric_contract` | `reported_arithmetic`, `exact_measurement_representation`, `exact_ranking_boundary` |
| `bootstrap` | `bootstrap_domain`, `bootstrap_identity_domain`, `schedule_identity_domain`, `replicate_count`, `block_length_rule`, `blocks_per_replicate_rule`, `schedule_rule`, `seed_domains`, `primary_interval`, `gated_incremental_interval` |
| `dispositions` | `primary`, `incremental`, `secondary_non_rescuing`, `invalid`, `inconclusive`, `reason_rule_identity` |
| `confirmation` | `continuation`, `population`, `chronology`, `scientific_contract`, `stopping_rule` |
| `artifacts` | `ranking_schema_identifier`, `evaluation_schema_identifier`, `ranking_artifact_identifier`, `evaluation_artifact_identifier`, `artifact_dependency_edges`, `artifact_dependency_graph_identity` |

Every sequence named above has the order stated in this decision or in the
adopted protocol. Identity-domain properties are literal domain strings, not
claimed digests. Identity properties are reconstructed digests. There are no
implementation-selected keys, optional branches, aliases, or extension maps.

The nested material is fixed as follows.

### 4.2 Protocol and execution profile

`protocol` binds the experiment identifier, supported protocol revision
`3112ab78a64f92892a70d5d4cbd17e1d14b1c2fe`, adopted protocol SHA-256,
Minimum-Effect decision identifier
`rq003-minimum-effect-scope-clarification-v1` and SHA-256, and source
convention revision `rq003-experiment-005-two-tier-source-v1`.

`execution_profile.execution_profile` is exactly `outcome_aware_v1`.
`research_specification_profile_identity` is reconstructed by
`ExecutionProfileBinding` under domain
`rq003-execution-profile-binding-v2`. The identity material is exactly
`canonical_encoding_version`, `execution_profile`, and `schema_version` as
defined by Research Execution Specification v2.
`adapter_profile_contract_identity` is independently reconstructed from the
six contracts by Section 9.1. Neither field may contain the other's value.

### 4.3 Source processing and dataset

`source_processing` binds:

- path `config/research/readiness/rq003-experiment-005-source-processing-v1.json`;
- its committed Git blob identity, byte count, and SHA-256;
- its governed decoder-configuration identity;
- projection-schema path and governed projection-schema identity; and
- source-processing prerequisite identifier
  `rq003-experiment-005-source-processing-prerequisite-v1` and SHA-256.

Each value must reconstruct from the committed Slice-2 bytes and existing
adapter-v3 identity domains. No value may be copied as an opaque assertion.

`dataset` binds dataset version `replay-dataset-v1`, lifecycle persisted
SHA-256
`7680856bc6a01f9b69be0921d6e66b3f43d5241a38e63b37871b6925c1d59ba7`,
external-input identifier `rq003-experiment-005-replay-source-v1`, the future
frozen manifest identity, and homogeneous source protocol revision
`3112ab78a64f92892a70d5d4cbd17e1d14b1c2fe`.

### 4.4 Decision, measurements, features, and procedures

`decision_selection` binds identifier
`end-slot-minus-5-latest-normal-v1`, identity
`203588f4a5acb6befd71c088a84145096f185addb8b605c386aa4c1f70bd9622`,
boundary `end_slot_minus_5`, chronology ascending `(start_slot, round_id)`,
`equal_rpc_tie_order` exactly
`["observed_at_utc","source_file","source_line_number"]`, and
`governed_exclusion_rules` exactly
`["no_predeclared_decision_observation","undefined_deployment_per_miner",
"zero_total_deployed_lamports","zero_total_miner_count"]` in that order.
These are the closed reasons enforced by `RankingExclusion.__post_init__` in
`orev3.experiments.rq003_experiment5_ranking`; the validator requires literal
vector equality and may not sort, extend, or introduce a new exclusion.

`candidate_order` is exactly the integer vector `0` through `24`.

`measurements.fundamental_measurement_pipeline_identity` is exactly the
exported `RQ003_PIPELINE_IMPLEMENTATION_IDENTITY` consumed by
`orev3.experiments.rq003_experiment5_ranking`.
`share_imbalance_definition_identity` is exactly exported
`EXPERIMENT5_SHARE_IMBALANCE_DEFINITION_IDENTITY` from
`orev3.experiments.rq003_experiment5`.
`deployment_per_miner_definition_identity` is
`governed_identity("deployment-per-miner-definition", material)`, where
`material` is exactly
`{"constructor_qualname":"orev3.experiments.rq003_experiment2a:deployment_per_miner",
"module_git_blob_identity":"e4bf90afe52f9b81025b53d43354c00bd30a4a77",
"module_sha256":"2c61d4ca0ee7cc252e75a516009e274b014f25135d51becf4cf1bc621ad6fc65"}`.
This binds the tracked constructor's exact zero-miner semantics rather than
restating them. The deployed-lamport and miner-count vector identity domain is
exactly `rq003-measurement-vector-v1`; their identities are reconstructed by
`MeasurementVector.reconstruct_vector_identity()` in
`orev3.features.rq003_execution` and distinguished by their closed ordered
output material. `mass` is not a predictive measurement.

`feature_set.feature_set_identity` is exactly exported
`EXPERIMENT5_FEATURE_SET_IDENTITY` from
`orev3.experiments.rq003_experiment5`; `ordered_fields` is exactly
`["signed_deployment_miner_share_imbalance"]`. It creates no additional
feature.

`procedures` is the following exact ordered vector:

| `name` | `role` | `rule` |
| --- | --- | --- |
| `share_imbalance_descending` | `primary` | `descending_exact_average_ties` |
| `deployment_per_miner_descending` | `incremental_control` | `descending_exact_average_ties` |
| `deterministic_baseline` | `uninformed_control` | `ascending_candidate_identifier` |
| `seeded_random_baseline` | `uninformed_control` | `rq003-experiment-005-seeded-random-v1` |
| `share_imbalance_ascending_sensitivity` | `non_rescuing_sensitivity` | `ascending_exact_average_ties` |

Before emitting any procedure, the validator reads exported
`EXPERIMENT5_PROCEDURE_IDENTITIES` from
`orev3.experiments.rq003_experiment5`, requires every tuple entry to have
exactly two elements `(name, identity)`, requires every name to be unique, and
requires every identity to be lowercase 64-hex. It then constructs exactly
`procedure_identity_by_name = {name: identity for name, identity in
EXPERIMENT5_PROCEDURE_IDENTITIES}` and requires its key set to equal the five
names in the table. Procedures are emitted only in the table's frozen order.
Duplicate, missing, or extra names reject. For each row,
`procedure_identity` is the exact mapped identity and `tie_identity` is that
same exact identity, because the canonical procedure material includes the
complete tie rule. Candidate identity never breaks a scientific tie.

### 4.5 Folds, metrics, numeric contract, and bootstrap

`folds_and_controls` has literal values `fold_count: 5`,
`fold_order: "five_consecutive_chronological_folds"`,
`adequate_support_per_fold: 100`,
`control_family_semantics: "all_adequate_controls_must_not_conflict"`, and
`sensitivity_semantics: "secondary_non_rescuing"`.
`comparability_identity_domain` is exactly
`rq003-experiment-005-comparability-v1`. `adequacy_rule_identity` is
`governed_identity("adequacy-rule", {"adequate_support":100,
"fold_count":5,"population":"complete_lifecycle_labeled_rounds",
"rule":"each_fold_support_greater_than_or_equal_to_100"})` using
`orev3.experiments.rq003_experiment5.governed_identity`.

All metric identities use domain `rq003-experiment-005-metric-v1` and material
`{"name": NAME, "definition": DEFINITION}` through
`orev3.experiments.rq003_experiment5.identity`. The ordered vectors are:

- `reciprocal_rank_metric_identities`: names
  `share_imbalance_mrr`, `deployment_per_miner_mrr`,
  `deterministic_baseline_mrr`, `seeded_random_baseline_mrr`, and
  `ascending_share_imbalance_mrr`, each with definition
  `mean_binary64_reciprocal_average_tie_rank`;
- `paired_vector_identities`: names
  `primary_minus_deterministic_baseline`,
  `primary_minus_seeded_random_baseline`, and
  `primary_minus_deployment_per_miner`, each with definition
  `ordered_round_level_binary64_reciprocal_rank_difference`;
- `primary_metric_identities`: the first reciprocal-rank metric followed by
  the first two paired-vector metrics;
- `incremental_metric_identities`: exactly
  `primary_minus_deployment_per_miner`; and
- `secondary_metric_identities`: exactly
  `ascending_share_imbalance_mrr` followed by the fold and comparability
  reports, whose names are `chronological_fold_report` and
  `comparability_report` and whose definition is
  `non_rescuing_deterministic_control_report`.

Names are mapped to their identities by the formula above and retain this
order. Every element stored in `reciprocal_rank_metric_identities`,
`paired_vector_identities`, `primary_metric_identities`,
`incremental_metric_identities`, and `secondary_metric_identities` is the
resulting exact lowercase 64-hex identity value. Metric names never appear in
an identity vector; names occur only in the identity material used to
reconstruct those values. No implementation-selected metric is permitted.

`numeric_contract.reported_arithmetic` is exactly the JSON string
`ieee_754_binary64_reciprocal_rank_paired_difference_mean_and_interval`.
`numeric_contract.exact_measurement_representation` is exactly
`reduced_signed_rational_positive_denominator`.
`numeric_contract.exact_ranking_boundary` is exactly
`exact_rational_order_then_binary64_average_tie_rank`. No decimal or alternate
floating-point contract is permitted.

`bootstrap` binds the deterministic circular moving-block bootstrap under
domain `rq003-experiment-005-moving-block-bootstrap-v1`, identity domain
`rq003-experiment-005-bootstrap-v1`, schedule identity domain
`rq003-experiment-005-bootstrap-schedule-v1`, exactly 10,000
replicates, block length `ceil(N^(1/3))`, `ceil(N/L)` circular blocks per
replicate truncated to `N`, and schedule rule
`shared_schedule_for_all_three_paired_vectors`. `seed_domains` is exactly the
ordered vector `["rq003-experiment-005-seeded-random-v1",
"rq003-experiment-005-moving-block-bootstrap-v1"]`. `primary_interval` is
exactly `two_sided_97.5_percent` and `gated_incremental_interval` is exactly
`two_sided_95_percent`. No replacement interval, schedule, or retry rule is
permitted.

The exact canonical JSON strings are
`bootstrap.block_length_rule: "ceil(N^(1/3))"` and
`bootstrap.blocks_per_replicate_rule: "ceil(N/L)"`.

### 4.6 Dispositions, confirmation, and artifacts

`dispositions.primary` is exactly the exported ordered tuple
`PRIMARY_DISPOSITIONS`; `dispositions.incremental` is exactly exported
`INCREMENTAL_DISPOSITIONS`; both come from
`orev3.experiments.rq003_experiment5_evaluation` without sorting.
`secondary_non_rescuing` is exactly `true`, `invalid` is exactly
`invalid_execution`, and `inconclusive` is exactly `evidence_insufficient`.
Reason construction is bound to tracked function
`orev3.experiments.rq003_experiment5_evaluation:resolve_primary_disposition`
and its committed module path
`src/orev3/experiments/rq003_experiment5_evaluation.py`.
`reason_rule_identity` is
`identity("rq003-experiment-005-disposition-reason-rule-v1", material)` where
`material` is the function qualname, module path, authenticated Git blob, and
module SHA-256 reconstructed from the future Slice-3 source commit. Each
emitted reason identity is
`identity("rq003-experiment-005-disposition-reason-v1",
{"disposition": disposition, "reason": reason})`; reasons outside that
function's reconstructed output reject. Secondary and sensitivity results
cannot rescue a failed primary family.

`confirmation` has exact literals
`continuation: "provisional_only"`,
`population: "one_immutable_disjoint_later_population"`,
`chronology: "strictly_later"`,
`scientific_contract: "same_frozen_experiment_005_contract"`, and
`stopping_rule: "no_performance_based_stopping"`. It does not select a
confirmation dataset.

`artifacts` binds:

- ranking schema identifier
  `rq003-experiment-005-ranking-artifact-schema-v1`;
- evaluation schema identifier
  `rq003-experiment-005-evaluation-report-schema-v1`;
- artifact identifiers `rq003-experiment-005-ranking-artifact-v1` and
  `rq003-experiment-005-evaluation-report-v1`; and
- `artifact_dependency_edges` exactly
  `[["authorization","evaluation"],["outcome_source","evaluation"],
  ["ranking","evaluation"]]`; and
- `artifact_dependency_graph_identity` equal to the future
  `evaluation_dependency_graph_identity` contract's `contract_identity`,
  reconstructed under domain `orev3:experiment-profile-contract:v1\n` from
  that closed contract excluding only its claimed `contract_identity`.

### 4.7 Configuration identity convention

The Experiment 005-specific configuration identity domain is exactly
`rq003-experiment-005-configuration-v1`. Its identity material is the complete
closed configuration object described in Sections 4.1 through 4.6 with only
the claimed `configuration_identity` property removed. Identity construction
is the existing canonical identity function:

```text
SHA-256(canonical_encode({
  "domain": "rq003-experiment-005-configuration-v1",
  "material": complete_configuration_without_configuration_identity
}))
```

`canonical_encode` is the existing repository identity encoding: the
canonical-encoding-version envelope, UTF-8, sorted keys, no insignificant
whitespace, finite numbers only, and no trailing bytes. The stored
configuration file is the corresponding closed canonical JSON object including
the reconstructed `configuration_identity`, followed by exactly one terminal
LF. The LF is part of the file byte count, file SHA-256, and Git blob, but not
an extra byte appended to `canonical_encode` identity material.

That Experiment-specific identity is then supplied as
`experiment_specific_configuration_identity` to
`ProfiledExperimentConfiguration` with the `outcome_aware_v1`
`ExecutionProfileBinding`. The final profiled
`experiment_configuration_identity` is reconstructed under the existing
domain `rq003-profiled-experiment-configuration-v2` from exactly
`canonical_encoding_version`, the Experiment-specific configuration identity,
the profile identity, and schema version `2`.

The future validator must independently reconstruct the file path, byte count,
SHA-256, Git blob identity, Experiment-specific identity, profile identity,
and final profiled identity. An opaque hash that merely equals a declared
value is insufficient.

### 4.8 Configuration schema and validator authority

The prospective configuration schema path is exactly
`src/orev3/execution/schemas/v1/rq003-experiment-005-configuration.schema.json`
and its identifier is exactly
`rq003-experiment-005-configuration-schema-v1`. It is a closed JSON Schema
using only keywords accepted by the current governed schema validator. Its
schema identity uses domain
`orev3:experiment-configuration-schema:v1\n` over canonical material
`{"path": path, "schema_identifier": identifier, "schema_sha256": sha256}`.

The prospective validator module path is exactly
`src/orev3/experiments/rq003_experiment5_configuration.py`, component
identifier `rq003-experiment-005-configuration-validator-v1`, and revision
`1`. Its worker kind is exactly the existing `CONTROLLER_PURE` kind. Its
component identity is reconstructed by the existing
`orev3.execution.phase3b_components:resolve_component` mechanism under domain
`orev3:experiment-phase3b-component-binding:v1\n` from exactly these six
fields and no others:

- `identifier`;
- `revision`;
- `path`;
- `git_object_identity`;
- `sha256`; and
- `worker_kind`.

Configuration-schema identity, protocol SHA-256, source-processing
prerequisite SHA-256, and configuration identity are authenticated separately
by validator/configuration authority and never enter component identity
material.

The current `COMPONENT_POLICIES` does not register this identifier, and current
adapter-v3 does not name a configuration validator component. Registration and
invocation are therefore blocked until the narrow readiness/adapter authority
prerequisite in Section 4.10 is adopted. That prerequisite may register this
fixed `CONTROLLER_PURE` component and its finite invocation point; it may not
create a new worker kind or descriptor-selected module/callable.

This decision freezes only the prospective validator identifier, revision,
path, existing worker kind, and existing six-field component identity formula.
It does not freeze or claim an existing registration or invocation. The future
narrow revision must specify exactly: the repository component-policy object
that registers it; the readiness/adapter validation stage that invokes it; the
closed input object supplied at that stage; the closed result object returned;
the adapter-acceptance check that consumes that result; and the independent
byte/path/blob/count/SHA reconstruction that prevents an opaque hash from
substituting for configuration bytes.

Once that prerequisite exists, the validator reads the exact authenticated
canonical configuration resource, rejects noncanonical or nonclosed material,
reconstructs the Experiment-specific identity, constructs
`ExecutionProfileBinding("outcome_aware_v1")`, constructs
`ProfiledExperimentConfiguration`, and verifies the final profiled identity.
It independently verifies the configuration schema and every separately
supplied resource binding. Missing, extra, opaque, or merely matching claimed
hashes reject.

### 4.9 Mandatory identity reconstruction vectors

Future conformance tests contain at least one positive canonical fixture and
one mutation for every top-level field. For a fixture `C`:

1. remove only `C["configuration_identity"]`, producing `M`; no other field is
   omitted;
2. compute `specific = identity("rq003-experiment-005-configuration-v1", M)`
   using `orev3.experiments.rq003_experiment5.identity` and its existing
   `canonical_encode` envelope;
3. require `C["configuration_identity"] == specific`;
4. construct `profile = ExecutionProfileBinding("outcome_aware_v1")` from
   `orev3.experiments.rq003_execution_specification_v2`;
5. construct
   `ProfiledExperimentConfiguration(profile, specific)` and require its
   `experiment_configuration_identity`; and
6. independently reconstruct the adapter profile-contract binding identity by
   `orev3.execution.contract_validation:reconstruct_profile_binding_identity`
   from profile name `outcome_aware_v1`, outcome policy
   `outcome_aware_authorized_only`, and the six authenticated contracts.

The value in step 2 is the Experiment-specific configuration identity. The
value in step 5 is the Research Execution Specification v2 profiled
configuration identity under domain
`rq003-profiled-experiment-configuration-v2`. The value in step 6 is the
adapter profile-contract binding identity under domain
`orev3:experiment-profile-binding:v1\n`. They are different authority domains,
are not interchangeable, and each mutation must change or invalidate every
downstream identity that consumes it.

### 4.10 Configuration-resource binding revision scope

**MODEL B — NARROW READINESS/ADAPTER AUTHORITY REVISION REQUIRED.**

**NARROW REVISION DESIGN SCOPE — NOT YET FROZEN IMPLEMENTATION AUTHORITY.**

Current adapter-v3 `configuration` contains only
`decision_selection_identity` and `experiment_configuration_identity`. It
does not declare or transport configuration path, Git object identity, byte
count, SHA-256, schema identity, or validator component identity. No current
implementation-binding field or other authoritative readiness object names
and authenticates the Experiment 005 configuration resource while making it
available to readiness validation. `governed_scope_paths` alone does not bind
the resource bytes and is insufficient.

Current frozen authority also does not define the exact adapter field name,
adapter schema placement, revised adapter schema version,
configuration-resource-binding identity domain, readiness evidence/record
cross-binding, or validator invocation stage. This decision does not invent
those choices or claim the future binding is already closed.

Accordingly, current authority can carry the final profiled
`experiment_configuration_identity` but cannot independently bind it to the
prospective configuration file. Before Slice-3 implementation, a narrow
prospective readiness/adapter revision must establish minimum semantics that
bind and independently reconstruct at least:

- `configuration_identifier`;
- `configuration_revision`;
- `configuration_path`;
- `configuration_git_object_identity`;
- `configuration_byte_count`;
- `configuration_sha256`;
- `configuration_schema_identifier`;
- `configuration_schema_path`;
- `configuration_schema_git_object_identity`;
- `configuration_schema_byte_count`;
- `configuration_schema_sha256`;
- `configuration_schema_identity`;
- `configuration_validator_identifier`;
- `configuration_validator_revision`;
- `configuration_validator_path`;
- `configuration_validator_git_object_identity`;
- `configuration_validator_sha256`;
- `configuration_validator_worker_kind`;
- `configuration_validator_component_identity`;
- claimed Experiment-specific configuration identity;
- reconstructed Experiment-specific configuration identity;
- claimed profiled `experiment_configuration_identity`; and
- reconstructed profiled `experiment_configuration_identity`.

That future revision must itself freeze one canonical
configuration-resource-binding identity domain and its exact identity material;
the exact adapter-v3 field/object placement; the exact revised adapter schema
version; the exact readiness validation stage; the exact object/evidence field
against which the binding is cross-checked; the validator's exact closed input
and result objects; how adapter acceptance consumes that result; and fail-closed
handling for every mismatch. It must require adapter
`configuration.experiment_configuration_identity` to equal the independently
reconstructed profiled identity. Until those choices are prospectively adopted,
the validator cannot be registered or invoked and the configuration resource
cannot enter adapter authority.

The narrow revision must not change scientific semantics, readiness lifecycle
states, evidence kinds, provider authority, or outcome capability. This
decision does not draft, adopt, or self-authorize that revision.

## 5. Official thin execution entry point

The only prospective official execution module path is
`src/orev3/experiments/rq003_experiment5_execution.py`. The only official entry
point is
`orev3.experiments.rq003_experiment5_execution:execute_experiment5`.

The ownership model is the existing orchestrator/gate model. The public
function accepts one closed mapping and returns one closed mapping. Its
mandatory `phase` discriminator accepts only `pre_outcome` and
`post_authorization`. The callable never owns or invokes an
`IndependentRankingFreezePort`, never freezes ranking, never builds or issues
`OutcomeAuthorization`, never issues or consumes `EvaluationCapability`, never
opens an outcome source, never allocates an attempt, and retains no mutable
cross-phase state.

### 5.1 Pre-outcome request and response

The `pre_outcome` request contains exactly:

- `phase: "pre_outcome"`;
- `experiment_configuration_bytes`;
- `experiment_configuration_identity` (Research Specification v2 profiled
  configuration identity);
- `replay_evidence` (authenticated generic Phase-3B Replay evidence);
- `projection_authority` (authenticated Experiment 005 closed projection and
  its schema/dataset authority);
- `selected_source_projection_bindings` (complete chronology-ordered tuple of
  existing `SelectedSourceProjectionBinding` values);
- `allocation_bundle` (the validated existing
  `orev3.execution.attempts:AllocationBundle`);
- `launch_authority` (the existing
  `orev3.execution.orchestrator:LaunchPrerequisiteAuthority` selected by the
  current-readiness resolver);
- `authenticated_launch_inputs` (the existing
  `orev3.execution.orchestrator:AuthenticatedLaunchInputs` returned by the
  launch authenticator);
- `attempt_namespace_identity`, which must equal
  `allocation_bundle.output_namespace_identity`; and
- `ranking_artifact_declaration_identity`.

The attempt identity is owned by `AllocationBundle.attempt_identity` and is
validated by `orev3.execution.attempts:validate_allocation_bundle`. The output
namespace identity is owned by `AllocationBundle.output_namespace_identity`,
is exposed in this interface as `attempt_namespace_identity`, and is checked by
the same allocation-bundle validator plus the declared attempt-output policy.
They are distinct fields and identity domains:
`attempt_identity != attempt_namespace_identity`. Equality between them is not
accepted as a substitute for independent validation.

The callable authenticates configuration and supplied scientific authority,
reconstructs the complete population, invokes only the official ranking
mechanics, constructs and semantically validates canonical RankingArtifact
bytes, and validates the declared ranking artifact material. It does not
freeze those bytes.

The `pre_outcome` response contains exactly:

- `phase: "pre_outcome"`;
- `ranking_candidate_bytes` (exact canonical RankingArtifact bytes);
- `ranking_artifact_identity`; and
- `declared_ranking_artifact_material`.

The response contains no freeze result, authorization, capability, or outcome
material.

### 5.2 Closed RankingContextAuthority construction

The existing orchestrator constructs
`orev3.execution.outcome_gate:RankingContextAuthority` from the pre-outcome
request and response using this exact mapping:

| RankingContextAuthority field | Authoritative source object/type | Exact source property | Required equality/cross-check |
| --- | --- | --- | --- |
| `attempt_identity` | `AllocationBundle` | `allocation_bundle.attempt_identity` | `validate_allocation_bundle(allocation_bundle)` passes and the value later equals `OutcomeGatePrerequisiteAuthority.attempt_identity` |
| `dataset_identity` | `LaunchPrerequisiteAuthority` | `launch_authority.dataset_identity` | equals `authenticated_launch_inputs.authority.dataset_identity` and later `OutcomeGatePrerequisiteAuthority.dataset_identity` |
| `external_input_snapshot_identities` | `AuthenticatedLaunchInputs` | `authenticated_launch_inputs.external_input_snapshot_identities` | `validate_authenticated_launch_inputs(slice2_prerequisite, launch_authority, prepared_launch_inputs, authenticated_launch_inputs)` passes; tuple equals `launch_authority.expected_external_input_snapshot_identities` and later the gate prerequisite tuple |
| `outcome_blind_provenance_identity` | `LaunchPrerequisiteAuthority` | `launch_authority.outcome_blind_provenance_identity` | equals `authenticated_launch_inputs.authority.outcome_blind_provenance_identity` and later the gate prerequisite value |
| `profile_identity` | `LaunchPrerequisiteAuthority` | `launch_authority.profile_identity` | equals `authenticated_launch_inputs.authority.profile_identity`, the adapter six-contract profile-binding identity, and later the gate prerequisite value |
| `ranking_contract_identity` | `LaunchPrerequisiteAuthority` | `launch_authority.ranking_contract_identity` | equals `authenticated_launch_inputs.authority.ranking_contract_identity` and later the gate prerequisite value |
| `ranking_freeze_component_identity` | `LaunchPrerequisiteAuthority` plus selected `IndependentRankingFreezePort` | `launch_authority.ranking_freeze_component_identity` and `freeze_port.freeze_component_identity` | both are non-null and equal; value later equals the gate prerequisite value |
| `ranking_freeze_contract_identity` | `LaunchPrerequisiteAuthority` | `launch_authority.ranking_freeze_contract_identity` | equals `authenticated_launch_inputs.authority.ranking_freeze_contract_identity` and later the gate prerequisite value |
| `ranking_reconstruction_component_identity` | `LaunchPrerequisiteAuthority` plus selected `IndependentRankingFreezePort` | `launch_authority.ranking_reconstruction_component_identity` and `freeze_port.reconstruction_component_identity` | both are non-null and equal; value later equals the gate prerequisite value |
| `replay_identity` | `LaunchPrerequisiteAuthority` | `launch_authority.replay_identity` | equals `authenticated_launch_inputs.authority.replay_identity`, the closed `replay_evidence["replay_identity"]`, and later the gate prerequisite value |

`authenticated_launch_inputs.authority` must be the same
`LaunchPrerequisiteAuthority` object by value. All identities are lowercase
64-hex. Snapshot identities are an immutable ordered tuple with no duplicates.
No field is inferred from a name, namespace, path, or neighboring identity.
Construction invokes the tracked `RankingContextAuthority` constructor. The
ranking candidate identity is not a context field; the freeze port reconstructs
it from `ranking_candidate_bytes`.

### 5.3 Exact freeze and authorization handoff

The handoff is exactly:

```text
execute_experiment5(phase="pre_outcome")
  -> RankingCandidate(ranking_candidate_bytes)
  -> OfficialOrchestrator invokes
     IndependentRankingFreezePort.freeze_and_reconstruct(candidate, context)
  -> RankingFreezeResult with frozen RankingAuthority
  -> validate_outcome_gate_authority reconstructs frozen bytes/authority
  -> build_outcome_authorization returns canonical OutcomeAuthorization
  -> OfficialOrchestrator issues EvaluationCapability
  -> EvaluationCapability.open_outcomes(OutcomeAuthorization)
  -> gate-owned outcome conversion and consumption receipt issuance
  -> AuthorizedExperiment5OutcomeMaterial
  -> execute_experiment5(phase="post_authorization")
```

The freeze port must return and later read exactly the original canonical
ranking bytes. Byte count and SHA-256 must match; reconstruction must produce
the same `RankingAuthority`. Changed, reserialized, or stale ranking bytes
reject.

### 5.4 Canonical authorization and subordinate gate-provenance interface

The execution authorization is exactly
`orev3.execution.outcome_gate:OutcomeAuthorization`, reconstructed from its
canonical bytes and required by `EvaluationCapability.open_outcomes`.
`orev3.experiments.rq003_experiment5_evaluation:EvaluationAuthorizationBinding`
is a separate scientific evaluation binding derived only after gate success:

```text
OutcomeAuthorization != EvaluationAuthorizationBinding
```

Neither substitutes for the other. The latter is constructed from the former
with `ranking_artifact_identity` equal to
`OutcomeAuthorization.material["frozen_ranking_artifact_identity"]`,
`outcome_source_identity` equal to its same-named material field, and
`authorization_identity` equal to `OutcomeAuthorization.identity`.

Semantic outcome opening occurs only when the existing gate-owned
`EvaluationCapability` consumes the exact canonical `OutcomeAuthorization`
and calls its sealed opener. The thin entry point never receives the
capability or opener.

Current gate authority returns the opener result but defines no canonical
Experiment 005 opened-outcome type, capability-consumption receipt, or
independently verifiable post-gate material. Therefore:

**SUBORDINATE OUTCOME-GATE PROVENANCE INTERFACE REQUIRED.**

The future subordinate interface is owned by the existing outcome-gate broker,
not the thin Experiment 005 callable. It must add these exact public authority
types/functions in `orev3.execution.outcome_gate`:

- `AuthenticatedOpenedExperiment5Outcome`;
- `EvaluationCapabilityConsumptionReceipt`;
- `AuthorizedExperiment5OutcomeMaterial`;
- gate-owned issuer
  `issue_authorized_experiment5_outcome_material` called only by
  `OfficialOrchestrator` immediately after successful capability consumption;
  and
- validator
  `validate_authorized_experiment5_outcome_material` called by the thin entry
  point before reading labels.

This decision freezes the minimum interface semantics but does not implement or
register it.

#### 5.4.1 Authenticated opening and deterministic label conversion

The sealed opener result must first reconstruct as
`AuthenticatedOpenedExperiment5Outcome` with exactly:

- `outcome_source_identity`;
- `opened_source_snapshot_identity`;
- `opened_outcome_provenance_identity`;
- `ordered_outcome_records`; and
- `authenticated_opened_outcome_identity`.

Its identity domain is exactly
`rq003-experiment-005-authenticated-opened-outcome-v1`. Its identity material is
the first four fields. `ordered_outcome_records` is an immutable vector ordered
ascending by `round_identity`; each closed record contains exactly
`round_identity`, `winning_square`, and `provenance`. Duplicate round identity,
noncanonical order, source mismatch, malformed winner, or unsupported
provenance rejects.

Inside the gate-owned issuer, and nowhere in the thin entry point, each record
is converted deterministically to
`orev3.experiments.rq003_experiment5_evaluation:OutcomeLabel` by passing the
record's three fields plus the authenticated `outcome_source_identity`.
The resulting immutable tuple retains ascending `round_identity` order. No
caller-supplied `OutcomeLabel` is accepted.

#### 5.4.2 Single-use consumption receipt

Each successful `EvaluationCapability.open_outcomes(OutcomeAuthorization)`
consumption produces exactly one gate-owned
`EvaluationCapabilityConsumptionReceipt`. It contains exactly:

- `evaluation_capability_identity`;
- `outcome_authorization_identity`;
- `attempt_identity`;
- `ranking_artifact_identity`;
- `ranking_freeze_identity`;
- `outcome_source_identity`;
- `opened_source_snapshot_identity`;
- `opened_outcome_provenance_identity`;
- `single_use_consumption_identity`; and
- `consumption_receipt_identity`.

The capability identity is assigned by the gate broker at issuance and bound
to the exact capability object, authorization, freeze result, and orchestrator
lifecycle. The single-use identity domain is exactly
`orev3:experiment-evaluation-capability-consumption:v1\n`; its material is the
first eight fields. The receipt identity domain is exactly
`orev3:experiment-evaluation-capability-consumption-receipt:v1\n`; its material
is all preceding receipt fields excluding only
`consumption_receipt_identity`.

In this interface, `ranking_freeze_identity` is not a new identity domain. It
is exactly `RankingFreezeResult.frozen_reference_identity` from the existing
gate-owned freeze result. The issuer and validator require literal equality;
no caller-supplied alias or independently claimed freeze digest is accepted.

The future subordinate gate-provenance interface records the capability
identity, single-use identity, receipt identity, exact receipt object issuance,
and consumed state in a gate-owned issuance registry. One capability can issue
one receipt and one post-gate material object only. Re-consumption, second
issuance, substituted receipt object, unknown receipt identity, or replay after
validation rejects.
The receipt is non-copyable and non-serializable like `EvaluationCapability`,
but non-forgeability rests on the broker's issuance record and named validator,
not constructor privacy or naming convention.

#### 5.4.3 Authorized post-gate material

`AuthorizedExperiment5OutcomeMaterial` contains exactly:

- `attempt_identity`;
- `ranking_artifact_identity`;
- `ranking_freeze_identity`;
- `outcome_authorization_identity`;
- `outcome_source_identity`;
- `consumption_receipt_identity`;
- `opened_outcome_provenance_identity`;
- `outcome_labels`; and
- `post_gate_material_identity`.

Its identity domain is exactly
`rq003-experiment-005-authorized-outcome-material-v1`; identity material is all
preceding fields excluding only `post_gate_material_identity`. Each label
contributes exactly `round_identity`, `winning_square`, `provenance`, and
`outcome_source_identity` in ascending round-identity order. The material's
receipt identity must equal the gate-issued receipt, and its opened provenance
must equal both the receipt and authenticated opener result.

`validate_authorized_experiment5_outcome_material(material,
outcome_authorization, ranking_freeze_result, ranking_authority)` reconstructs
both identities; verifies the exact gate-issued receipt object and broker
issuance record; verifies attempt, authorization, source, ranking, freeze,
snapshot/provenance, capability-consumption, and label canonicality; atomically
marks that receipt delivered to this one post-authorization evaluation; and
returns the validated immutable OutcomeLabel tuple. A replayed or superseded
receipt/material rejects. This function does not open outcomes or grant a
second capability.

### 5.5 Post-authorization request and response

The `post_authorization` request contains exactly:

- `phase: "post_authorization"`;
- `experiment_configuration_bytes`;
- `experiment_configuration_identity`;
- `allocation_bundle` (the same validated `AllocationBundle` used before
  ranking);
- `attempt_namespace_identity`, equal to
  `allocation_bundle.output_namespace_identity`;
- `ranking_artifact_bytes` (the exact bytes read back from the freeze port);
- `ranking_artifact_identity`;
- `ranking_freeze_result` (the exact existing `RankingFreezeResult` produced by
  the orchestrator-owned freeze port);
- `ranking_authority` (the exact frozen `RankingAuthority`);
- `outcome_authorization` (canonical `OutcomeAuthorization`);
- `adapter_profile_identity`;
- `authorized_outcome_material` (the gate-produced
  `AuthorizedExperiment5OutcomeMaterial`);
- `evaluation_artifact_declaration_identity`; and
- `audit_manifest_declaration_identity`.

The callable reconstructs all authority and requires: request
`allocation_bundle.attempt_identity` equals the authorization, frozen ranking
authority, and authorized outcome material attempt;
`validate_allocation_bundle(allocation_bundle)` passes; request
`attempt_namespace_identity` equals
`allocation_bundle.output_namespace_identity` and the declared output-policy
namespace; ranking bytes round-trip canonically and
match `ranking_freeze_result.ranking_byte_count`,
`ranking_freeze_result.ranking_sha256`, its `ranking_authority`, and both
ranking identities; `adapter_profile_identity` equals the
authorization and frozen authority profile; outcome authorization identity
and outcome-source identity equal the post-gate material. Before reading any
label it calls
`validate_authorized_experiment5_outcome_material(authorized_outcome_material,
outcome_authorization, ranking_freeze_result, ranking_authority)` and uses only
the immutable label tuple returned by that validator. It then derives
`EvaluationAuthorizationBinding` as specified in Section 5.4, invokes the
official evaluation mechanics, validates EvaluationReport, and constructs the
terminal Research Specification v2 Experiment Audit Manifest.

The response contains exactly:

- `phase: "post_authorization"`;
- `evaluation_report_bytes`;
- `evaluation_report_identity`;
- `experiment_audit_manifest_material`;
- `experiment_audit_manifest_identity`; and
- `declared_terminal_artifact_material`.

Changed or stale ranking, authorization for another attempt, source mismatch,
profile mismatch, missing gate provenance, arbitrary OutcomeLabel injection,
invalid or replayed consumption receipt, superseded post-gate material,
noncanonical label vector, evaluation before freeze, evaluation before
authorization, unknown phase, and missing or extra request fields all fail
closed. The response contains no
provider, allocation, runtime-control, wallet, or capital authority.

The entry point orchestrates scientific mechanics only. It does not locate or
choose data, write outside the declared attempt namespace, reproduce or fork
scientific formulas, or change ranking after outcome access.

## 6. Ranking artifact structural authority

The prospective schema path is
`src/orev3/execution/schemas/v1/rq003-experiment-005-ranking-artifact.schema.json`
and its schema identifier is
`rq003-experiment-005-ranking-artifact-schema-v1`. The schema is one closed
top-level object with closed nested structures matching the current
`RankingArtifact.to_material()` representation. Its top level contains
exactly:

- `schema_version`;
- `experiment_identifier`;
- `protocol_sha256`;
- `information_flow`;
- `authority`;
- `candidate_order`;
- `population_accounting`;
- `ordered_replay_round_identities`;
- `ranking_records`;
- `exclusions`;
- `ranking_audits`; and
- `ranking_artifact_identity`.

It requires outcome-blindness, exact population accounting, authenticated
selected-source and measurement authority, complete procedure authority,
canonical ranks and ties, deterministic reconstruction, Replay dependency,
and reconstruction of identity domain
`rq003-experiment-005-ranking-artifact-v1`. It recursively rejects outcome,
label, authorization, evaluation, provider, opener, and join capability or
material.

The JSON Schema is structural authority only. The frozen Python
`RankingArtifact.from_canonical_bytes()` reconstruction remains the semantic
validator and must accept the same canonical bytes. Schema acceptance without
semantic reconstruction is insufficient.

## 7. Evaluation report structural authority

The prospective schema path is
`src/orev3/execution/schemas/v1/rq003-experiment-005-evaluation-report.schema.json`
and its schema identifier is
`rq003-experiment-005-evaluation-report-schema-v1`. The schema is one closed
top-level object with closed nested structures matching the current
`EvaluationReport.to_material()` representation. Its top level contains
exactly:

- `schema_version`;
- `experiment_identifier`;
- `protocol_sha256`;
- `ranking_artifact_identity`;
- `authorization_identity`;
- `outcome_source_identity`;
- `evaluation_records`;
- `missing_round_identities`;
- `outcome_join_report`;
- `population_accounting`;
- `comparability`;
- `chronological_fold_report`;
- `controls`;
- `metrics`;
- `round_level_paired_vectors`;
- `bootstrap`;
- `primary_disposition`;
- `primary_reasons`;
- `incremental_disposition`;
- `confirmation_boundary`;
- `evaluation_audits`; and
- `evaluation_report_identity`.

It requires exact ranking dependency, attempt-local authorization binding,
immutable outcome-source binding, complete labeled/missing partition,
fold/control and metric reconstruction, paired vectors, deterministic
bootstrap, primary and incremental dispositions, confirmation continuation,
and reconstruction under identity domain
`rq003-experiment-005-evaluation-report-v1`.

The JSON Schema is structural authority only. The frozen Python
`EvaluationReport.from_canonical_bytes()` reconstruction remains the semantic
validator and must accept the same canonical bytes. Schema acceptance without
semantic reconstruction is insufficient.

## 8. Replay artifact decision

**REPLAY MANIFEST NOT NEEDED AS SEPARATE ADAPTER ARTIFACT.**

Generic Replay evidence already exists in Phase 3B;
`SelectedSourceProjectionBinding` carries authenticated source/projection
authority; RankingArtifact authority binds Replay identity; the ranking
artifact dependency role is `replay`; and the terminal Experiment Audit
Manifest binds terminal provenance. A separate Replay adapter artifact would
duplicate authority without retiring a distinct failure mode. Slice 3 must not
declare one.

## 9. Profile-contract paths and contents

The future profile has exactly these six contract paths:

1. `config/research/readiness/profiles/rq003-experiment-005-authorization-contract-v1.json`;
2. `config/research/readiness/profiles/rq003-experiment-005-evaluation-dependency-graph-v1.json`;
3. `config/research/readiness/profiles/rq003-experiment-005-ranking-freeze-contract-v1.json`;
4. `config/research/readiness/profiles/rq003-experiment-005-outcome-blind-ranking-source-v1.json`;
5. `config/research/readiness/profiles/rq003-experiment-005-outcome-source-contract-v1.json`; and
6. `config/research/readiness/profiles/rq003-experiment-005-ranking-artifact-reference-v1.json`.

Each contract is validated by the tracked schema
`src/orev3/execution/schemas/v1/profile-contract.schema.json` and profile-contract
v1 semantic authority in `src/orev3/execution/contract_validation.py`. Each
contains exactly the fields
allowed by `_OUTCOME_AWARE_CONTRACT_FIELDS` for its contract kind and contains
no `schema_version` property. Each independently reconstructs
`contract_identity` under domain
`orev3:experiment-profile-contract:v1\n` after removing only the claimed
identity. Their exact kinds and dependencies are:

- authorization contract: identifier `authorization_contract_identity`, kind
  `outcome-authorization`, evaluation artifact identifier
  `rq003-experiment-005-evaluation-report-v1`, and
  `outcome_access: authorization_required`;
- evaluation dependency graph: identifier
  `evaluation_dependency_graph_identity`, kind
  `evaluation-dependency-graph`, ranking artifact identifier
  `rq003-experiment-005-ranking-artifact-v1`, evaluation artifact identifier
  `rq003-experiment-005-evaluation-report-v1`, and exactly the three ordered
  edges fixed in Section 4.6;
- ranking freeze contract: identifier `freeze_contract_identity`, kind
  `ranking-freeze`, ranking artifact identifier
  `rq003-experiment-005-ranking-artifact-v1`, and
  `ranking_frozen_before_outcome: true`;
- outcome-blind ranking source: identifier
  `outcome_blind_ranking_source_identity`, kind
  `outcome-blind-ranking-source`, ranking artifact identifier
  `rq003-experiment-005-ranking-artifact-v1`, and `outcome_blind: true`;
- outcome source contract: identifier `outcome_source_identity`, kind
  `outcome-source`, external-input identifier
  `rq003-experiment-005-replay-source-v1`, and
  `outcome_source_role: declared_external_input`; and
- ranking artifact reference: identifier `ranking_artifact_identifier`, kind
  `ranking-artifact-reference`, and artifact identifier
  `rq003-experiment-005-ranking-artifact-v1`.

These files bind declarations and dependencies only. None grants runtime,
filesystem, provider, outcome, evaluation, allocation, or capital capability.

### 9.1 Two distinct profile identities

The Research Execution Specification v2 identity is
`ExecutionProfileBinding("outcome_aware_v1").profile_identity`, reconstructed
under `rq003-execution-profile-binding-v2`. It exists inside
`ProfiledExperimentConfiguration` and the scientific ExperimentProtocolV2
binding.

The adapter profile-contract binding identity is reconstructed by
`orev3.execution.contract_validation:reconstruct_profile_binding_identity`
under `orev3:experiment-profile-binding:v1\n`, with profile name
`outcome_aware_v1`, outcome policy `outcome_aware_authorized_only`, and the six
contract identities in sorted contract-identifier order.

These identities are different and not interchangeable. The future
configuration uses the Research Specification v2 profile identity where
`ProfiledExperimentConfiguration` requires it. The implementation binding,
adapter descriptor, profile validation, and readiness cross-checks use the
adapter profile-contract binding identity wherever their current schemas call
the field `profile_identity`. Cross-check code must reconstruct both and reject
substitution of one for the other.

## 10. Implementation-binding convention

The future binding path is
`config/research/readiness/experiments/rq003-experiment-005-implementation-binding-v1.json`.
It is closed under the existing implementation-binding schema and binds:

- `schema_version: 1`;
- adapter identifier `rq003-experiment-005-adapter-v3`;
- experiment identifier
  `rq003-experiment-005-signed-share-imbalance-predictive-evaluation`;
- entry point
  `orev3.experiments.rq003_experiment5_execution:execute_experiment5`;
- the reconstructed Research Execution Specification v2 identity;
- the reconstructed profiled Experiment 005 configuration identity;
- the adapter profile-contract binding identity reconstructed from the six
  contracts and `outcome_aware_authorized_only` policy;
- adopted protocol identifier, revision, and SHA-256;
- `protocol_binding_identity` reconstructed exactly by
  `orev3.execution.readiness_record:reconstruct_protocol_binding_identity`
  from the complete implementation-binding material after removing only the
  claimed `protocol_binding_identity`; and
- implementation module path, Git blob identity, and SHA-256 for
  `src/orev3/experiments/rq003_experiment5_execution.py`.

Every identity must reconstruct from committed bytes and governed material.
No opaque implementation identity or matching claimed hash may substitute for
the committed module binding.

`ExperimentProtocolV2Binding.experiment_binding_identity` remains separate
scientific/configuration authority. It does not populate and cannot substitute
for the implementation binding's `protocol_binding_identity`. Likewise, the
Research Specification v2 `ExecutionProfileBinding.profile_identity` remains
available to the profiled configuration but cannot substitute for the adapter
profile-contract binding identity required by current implementation-binding
and readiness validators.

## 11. Required future Slice-3 build order

Any later separately authorized Slice-3 construction must follow this exact
dependency order:

```text
external-input manifest authority
  -> ranking/evaluation/configuration schema bytes and identities
  -> narrow readiness/adapter configuration-binding revision
  -> configuration-validator component registration
  -> six profile-contract bytes and identities
  -> adapter profile-contract binding identity
  -> Experiment 005-specific configuration material
  -> Research Specification v2 profiled configuration identity
  -> gate-owned outcome-material issuance/provenance interface
  -> thin entry-point bytes
  -> implementation binding
  -> artifact declarations and attempt-output identity
  -> adapter descriptor
  -> production registry
```

The narrow readiness/adapter revision supplies the configuration-resource
binding and fixed validator invocation described in Section 4.10; component
registration cannot precede it. The profile contracts consume the resolved
combined outcome-source identifier from Section 3.2 and final
ranking/evaluation artifact identifiers; they do not consume configuration or
entry-point identities. The configuration consumes the completed schema and
adapter profile-contract identities. A separate subordinate outcome-gate
provenance-interface authority must prospectively add the types, issuer,
receipt, conversion, validator, and single-use broker checks in Section 5.4
before the thin entry point is implemented. It need not add a readiness
lifecycle state or evidence kind, and this decision does not adopt it. No
cycle is present. Each step consumes final identities from the preceding
steps. Registry adoption must use the complete final descriptor bytes.
Descriptor members, identities, declarations, and bindings cannot be
placeholders or filled after registry adoption.

## 12. Explicit non-authorizations

This decision creates no authority for:

- production adapter creation or adoption;
- production registry modification;
- implementation, configuration, schema, profile-contract, binding, or
  declaration creation;
- final Source S or dataset promotion;
- readiness evidence, a readiness candidate, READINESS_VALIDATED, E, R, or
  EXECUTION_READY;
- adoption or implementation of the narrow readiness/adapter revision;
- adoption or implementation of the subordinate outcome-gate provenance
  interface;
- provider, backend, namespace, allocation, or control authority;
- STARTED or any experiment/ranking execution;
- outcome location, opening, parsing, authorization, or evaluation execution;
- confirmation-dataset selection;
- Strategy or Paper Miner admission or work; or
- wallet, transaction, capital, or SOL access or use.

This decision grants no authority-changing next step. The narrow
readiness/adapter revision and the subordinate outcome-gate provenance
interface each require separate prospective authority and adoption. A
coordinator may separately authorize bounded Slice-3 construction only after
both prerequisites are adopted and independently verified. That later task
must still stop before any registry adoption, Source S, readiness, or execution
authority not expressly authorized at that time.
