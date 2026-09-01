# RQ-003 Experiment 005 Configuration-Resource Readiness Revision v1

- Type: Prospective subordinate readiness/adapter governance decision
- State: Adopted and frozen prospectively
- Experiment: `rq003-experiment-005-signed-share-imbalance-predictive-evaluation`
- Decision revision: `rq003-experiment-005-configuration-resource-readiness-revision-v1`
- Scientific disposition: `SCIENTIFICALLY COMPATIBLE`
- Readiness disposition: `NARROW ADAPTER/READINESS REVISION`
- Readiness sufficiency disposition: `NARROW ADAPTER/READINESS REVISION SUFFICIENT`
- Readiness-record schema revision required: No
- Evidence-kind revision required: No
- Implementation authorized: No
- Adapter adoption authorized: No
- Registry modification authorized: No
- Source S established: No
- Execution authorized: No
- Outcome access authorized: No

## 1. Purpose and controlling authority

This decision prospectively freezes the subordinate authority needed to
authenticate an Experiment configuration resource through adapter declaration
v4 and independent readiness reconstruction. It repairs one configuration-byte
trust boundary. It does not implement that repair or create an adapter,
configuration, Source S, readiness result, or execution authority.

The adopted Slice-3 authority prerequisite at
`docs/research/governance/rq003-experiment-005-slice3-authority-prerequisite-v1.md`,
SHA-256
`d3e8748c63f0a870a3b1e1439fa73ada0145c7502bccc8fd834987e8fb29a36e`,
remains controlling. In particular, its Experiment-specific configuration
identity, Research Specification v2 profiled identity, configuration schema,
validator coordinates, profile-identity distinction, scientific semantics,
dependency order, and non-authorizations are unchanged.

## 2. Failure mode and repaired trust boundary

Adapter declaration v3 binds only these fields inside `configuration`:

- `decision_selection_identity`; and
- `experiment_configuration_identity`.

It does not independently authenticate the configuration path, Git object,
byte count, SHA-256, schema authority, or finite validator component. An
adapter must not pass readiness merely because it presents a valid-looking or
equality-consistent `experiment_configuration_identity`.

The future revision must independently prove all of the following from the
approved source commit S:

1. the exact committed configuration bytes and resource coordinates;
2. the exact committed configuration-schema bytes and schema identity;
3. the exact finite repository-owned validator component;
4. the Experiment 005-specific configuration identity;
5. the Research Specification v2 profiled configuration identity; and
6. equality of the reconstructed profiled identity across adapter and
   implementation-binding authority.

No claimed hash, coordinated resealing, or equality among untrusted claims can
substitute for reconstruction from committed bytes.

## 3. Adapter declaration version model

Existing adapter declaration schemas v1, v2, and v3 remain immutable. This
decision does not reinterpret adapter-v3. The new same-kind revision is v4
with these exact prospective coordinates:

| Property | Exact value |
| --- | --- |
| Semantic kind | `adapter-declaration` |
| Registry identifier | `adapter-declaration-v4` |
| Schema path | `src/orev3/execution/schemas/v1/adapter-declaration-v4.schema.json` |
| Schema `$id` | `orev3://schemas/execution-readiness/v1/adapter-declaration-v4` |
| Schema title | `AdapterDeclarationV4` |
| Descriptor `schema_version` | `4` |
| Adapter identity domain | `orev3:readiness-adapter-declaration:v1\n` |

V4 retains the complete v3 semantic field set without changing the meaning of
any v3 field. It additionally requires the configuration-resource binding in
Section 4. Adapter identity continues to be reconstructed by the existing
adapter identity mechanism over the complete v4 descriptor excluding only its
claimed `adapter_identity`. The unchanged domain does not make v3 and v4
interchangeable because `schema_version` and the required v4 resource object
participate in the descriptor material.

### 3.1 Exact cross-stage generation and overlays

The one prospective governed generation for this revision is exactly:

```text
ProspectiveRegistryGeneration.ADAPTER_V4_CONFIGURATION_RESOURCE
```

Its serialized value is exactly:

```text
prospective-v1.1-adapter-v4-configuration-resource
```

The same member name and serialized value are added to
`PreparationAuthorityGeneration` and `EvidenceAuthorityGeneration`. These are
three stage-local enum types carrying one identical governed generation value;
they do not define three independently selectable authority generations.

`src/orev3/execution/readiness_record.py` defines exactly these six new
overlay constants:

- `PROSPECTIVE_ADAPTER_V4_PHASE3A_SCHEMA_POLICY`;
- `PROSPECTIVE_ADAPTER_V4_PHASE3A_SCHEMA_DOCUMENT_POLICY`;
- `PROSPECTIVE_ADAPTER_V4_PHASE3B_SCHEMA_POLICY`;
- `PROSPECTIVE_ADAPTER_V4_PHASE3B_SCHEMA_DOCUMENT_POLICY`;
- `PROSPECTIVE_ADAPTER_V4_READINESS_SCHEMA_POLICY`; and
- `PROSPECTIVE_ADAPTER_V4_READINESS_SCHEMA_DOCUMENT_POLICY`.

Each is copied from its existing v3 counterpart with exactly one same-kind
replacement: semantic kind `adapter-declaration` changes from the v3 schema
coordinates to the v4 coordinates in Section 3. All other members, order, and
document bindings remain unchanged. Phase-3A, Phase-3B, and final overlay
counts remain exactly 10, 20, and 29.

`readiness_contracts._PROSPECTIVE_POLICIES` maps
`ProspectiveRegistryGeneration.ADAPTER_V4_CONFIGURATION_RESOURCE` only to the
29-member `PROSPECTIVE_ADAPTER_V4_READINESS_SCHEMA_POLICY` and its document
policy. Phase-3A selection uses the named Phase-3A pair; Phase-3B selection
uses the named Phase-3B pair. No implicit stage selection exists.

The detached Phase-3A and Phase-3B request field is exactly
`authority_generation`, with exact value
`"prospective-v1.1-adapter-v4-configuration-resource"`. The Phase-3B
controller passes that same value unchanged to its Phase-3A sibling request.

`CurrentReadinessInput` gains the exact field
`authority_generation: ProspectiveRegistryGeneration`. Its backward-compatible
default is `ProspectiveRegistryGeneration.READINESS_V1_1`. Experiment 005 v4
current-readiness construction must explicitly supply
`ProspectiveRegistryGeneration.ADAPTER_V4_CONFIGURATION_RESOURCE`; that value
selects the matching final overlay for both prerequisite loading and schema
registry reconstruction. A record or descriptor cannot select or override the
generation.

`load_readiness_prerequisite_contracts` gains the keyword-only parameter
`generation: ProspectiveRegistryGeneration =
ProspectiveRegistryGeneration.READINESS_V1_1`. Existing callers retain the
current final overlay. Every v4 caller, including current readiness, must pass
`ProspectiveRegistryGeneration.ADAPTER_V4_CONFIGURATION_RESOURCE` explicitly.
The Phase-3A and Phase-3B schema loader functions likewise receive their
stage-local generation enums and reject every value other than their exact
historical/current members and `ADAPTER_V4_CONFIGURATION_RESOURCE`.

## 4. Exact descriptor placement

Adapter-v4 contains the resource object only at
`descriptor.configuration.experiment_configuration_resource`.
`descriptor.configuration` is closed and contains exactly:

- `decision_selection_identity`;
- `experiment_configuration_identity`; and
- `experiment_configuration_resource`.

Top-level placement, implementation-binding-owned placement, a separately
referenced declaration, duplicate placement, aliases, or extension maps are
prohibited.

## 5. Closed configuration-resource object

`experiment_configuration_resource` is a closed object containing exactly:

1. `schema_version`;
2. `configuration_identifier`;
3. `configuration_revision`;
4. `configuration_path`;
5. `configuration_git_object_identity`;
6. `configuration_byte_count`;
7. `configuration_sha256`;
8. `configuration_schema_identifier`;
9. `configuration_schema_revision`;
10. `configuration_schema_path`;
11. `configuration_schema_git_object_identity`;
12. `configuration_schema_byte_count`;
13. `configuration_schema_sha256`;
14. `configuration_schema_identity`;
15. `configuration_validator_identifier`;
16. `configuration_validator_revision`;
17. `configuration_validator_path`;
18. `configuration_validator_git_object_identity`;
19. `configuration_validator_sha256`;
20. `configuration_validator_worker_kind`;
21. `configuration_validator_component_identity`;
22. `experiment_specific_configuration_identity`;
23. `profiled_experiment_configuration_identity`; and
24. `configuration_resource_identity`.

No field is optional. No additional property is accepted. Exact fixed values
for Experiment 005 are:

| Field | Exact value |
| --- | --- |
| `schema_version` | `1` |
| `configuration_identifier` | `rq003-experiment-005-configuration-v1` |
| `configuration_revision` | `"1"` |
| `configuration_schema_identifier` | `rq003-experiment-005-configuration-schema-v1` |
| `configuration_schema_revision` | `"1"` |

Paths use the existing canonical repository-path grammar. Git object
identities, SHA-256 values, and all claimed identities use their existing
closed lowercase grammar. Byte counts are nonnegative integers and booleans
are rejected as integers.

## 6. Configuration-resource identity

The claimed field is `configuration_resource_identity`. Its identity domain is
exactly:

```text
orev3:readiness-adapter-experiment-configuration-resource:v1\n
```

It reconstructs as:

```text
domain_identity(
  "orev3:readiness-adapter-experiment-configuration-resource:v1\n",
  complete_experiment_configuration_resource_without_only_configuration_resource_identity
)
```

The existing canonical encoding and `domain_identity` implementation are
controlling. Every other immutable resource field participates. No field other
than the claimed `configuration_resource_identity` is excluded. Reordering,
omission, aliasing, normalization, or a parallel Experiment-specific resource
domain is prohibited.

## 7. Required configuration equalities

Readiness must establish this exact equality chain:

```text
descriptor.configuration.experiment_configuration_identity
== descriptor.configuration.experiment_configuration_resource
     .profiled_experiment_configuration_identity
== implementation_binding.experiment_configuration_identity
== independently_reconstructed_profiled_experiment_configuration_identity
```

The authenticated result in Section 14 must carry that same reconstructed
profiled identity. Any mismatch rejects. Equality of claimed values before
independent reconstruction is insufficient.

## 8. Configuration-schema authority

The Experiment 005 configuration-schema coordinates are exactly:

| Property | Exact value |
| --- | --- |
| Path | `src/orev3/execution/schemas/v1/rq003-experiment-005-configuration.schema.json` |
| Identifier | `rq003-experiment-005-configuration-schema-v1` |
| Revision | `"1"` |

The resource binds schema identifier, revision, path, Git object identity,
byte count, SHA-256, and schema identity. Schema identity reconstructs exactly:

```text
domain_identity(
  "orev3:experiment-configuration-schema:v1\n",
  {
    "path": configuration_schema_path,
    "schema_identifier": configuration_schema_identifier,
    "schema_sha256": configuration_schema_sha256
  }
)
```

Git object identity, byte count, and revision remain transitively bound by
`configuration_resource_identity`; they do not enter the schema identity
formula. The schema must be a tracked safe regular Git blob with exact mode
`100644`, canonical JSON bytes, a closed object model, and only keywords
accepted by the governed schema validator. Its `$id`, where required by the
future schema overlay, must equal the overlay’s exact declared identifier.

## 9. Finite validator component authority

The only prospective validator component is:

| Property | Exact value |
| --- | --- |
| Identifier | `rq003-experiment-005-configuration-validator-v1` |
| Revision | `1` |
| Path | `src/orev3/experiments/rq003_experiment5_configuration.py` |
| Worker kind | `CONTROLLER_PURE` |

It must be registered in the existing
`orev3.execution.phase3b_components:COMPONENT_POLICIES`. No new component
policy family or worker kind is introduced. Resolution must use existing
`orev3.execution.phase3b_components:resolve_component` authority. Component
identity material contains exactly:

- `identifier`;
- `revision`;
- `path`;
- `git_object_identity`;
- `sha256`; and
- `worker_kind`.

The domain remains
`orev3:experiment-phase3b-component-binding:v1\n`. Schema identity,
configuration identity, protocol identity, and prerequisite identity do not
enter component identity material; they are cross-bound separately.

Descriptors may name only the registered validator identifier. They may not
supply a module name, callable, path override, worker override, unregistered
component, or arbitrary callback.

## 10. CONTROLLER_PURE capability boundary

The validator is pure controller validation. It receives only authenticated
governed bytes and closed authority objects. Repository path resolution,
committed-object loading, schema selection, and component policy resolution
remain controller-owned authority and are not descriptor-selected
capabilities.

The validator receives no network, provider/backend, allocation, outcome,
evaluation, wallet, transaction, or arbitrary filesystem capability. Any
filesystem access is limited to controller resolution of exact paths already
approved by Source-S scope authority. No new Phase-3B worker profile is
required, and the `CONTROLLER_PURE` closure must remain free of outcome- or
provider-capable dependencies.

### 10.1 Finite identifier-specific controller closure

`src/orev3/execution/phase3b_components.py` adds exactly one dedicated mapping
named:

```text
CONTROLLER_PURE_COMPONENT_CLOSURES
```

It is a closed repository-owned mapping from component identifier to an exact
ordered tuple of repository-relative Python source paths. Its required key is
exactly:

```text
rq003-experiment-005-configuration-validator-v1
```

The value is the complete finite import/execution closure for that validator.
The value is exactly this authority-bearing ordered tuple:

```text
(
  "src/orev3/execution/canonical.py",
  "src/orev3/features/rq003_contracts.py",
  "src/orev3/experiments/rq003_experiment5_configuration.py",
)
```

The tuple order is fixed as readiness canonical/schema mechanics, RQ-003
canonical identity mechanics, then the validator entry module. The first path
supplies strict canonical readiness JSON, schema validation, and readiness
domain identities. The second supplies only the existing RQ-003
`CANONICAL_ENCODING_VERSION` and `canonical_encode` envelope required to
reconstruct the already-frozen Experiment-specific and Research Specification
v2 profiled identities. The third is the exact validator implementation and
owns the closed configuration field checks and the static reconstruction of
those frozen identity materials. It must not import
`rq003_experiment5.py`, `rq003_execution_specification.py`, or
`rq003_execution_specification_v2.py`; importing those broader scientific,
filesystem-writing, or outcome-aware surfaces is prohibited. It must not
redefine either canonical encoder.

No package-directory wildcard, prefix expansion, runtime import discovery,
descriptor-supplied dependency list, ambient `PYTHONPATH` dependency, arbitrary
module/callback loading, or unlisted repository module is permitted. Each path
appears exactly once. Tuple order is authority-bearing and must be preserved.

No other repository-owned Python path is a closure member. Future Git object
and SHA-256 values are derived from the approved implementation commit bytes;
they are not implementation-author choice once the finite tuple is committed
and reviewed.

### 10.2 Closure authentication and import semantics

For every tuple path, the controller must resolve the path from the approved
Source-S commit, require a tracked safe regular Git blob with exact mode
`100644`, authenticate its Git object identity and SHA-256, verify it lies
within governed Source-S scope, and include it exactly once in the authenticated
closure material. The component’s own module remains independently bound by
`resolve_component` and must equal its entry in the authenticated closure.

The exact resolver is
`orev3.execution.phase3b_components:resolve_controller_pure_component_closure`.
It accepts only `(repository, source_commit, identifier)` and returns an ordered
tuple of frozen `ControllerPureClosureMember` values. Each member contains
exactly `path`, `git_object_identity`, and `sha256`, in mapping tuple order.
The returned path vector must equal
`CONTROLLER_PURE_COMPONENT_CLOSURES[identifier]` literally. No caller-supplied
member, path, order, digest, policy, or closure override is accepted.

Authentication rejects a missing or extra dependency, tuple reordering, path,
blob, or hash substitution, non-`100644` mode, non-blob/tree/symlink-like
object, import outside the governed tuple, outcome/provider/evaluation-capable
dependency, runtime-discovered import, descriptor-selected dependency, or
ambient-path resolution.

The validator is imported and executed only from this authenticated finite
closure. The exact path-to-module mapping is fixed and admits no aliases:

```text
src/orev3/execution/canonical.py
  -> orev3.execution.canonical
src/orev3/features/rq003_contracts.py
  -> orev3.features.rq003_contracts
src/orev3/experiments/rq003_experiment5_configuration.py
  -> orev3.experiments.rq003_experiment5_configuration
```

This is also the complete application of the general mapping rule: remove the
single leading `src/`, remove the single terminal `.py`, and replace `/` with
`.`. Caller-supplied names, aliases, rebasing, alternate package roots, and
case or Unicode normalization are prohibited.

The exact import-session owner is `ControllerPureImportSession`, implemented
only in `src/orev3/execution/phase3b_components.py`. For one validator call it
owns the complete `sys.modules` snapshot, removal, delta tracking, and
restoration; guarded builtins; guarded import function; finder installation;
authenticated loader construction; namespace-shell creation; and deterministic
cleanup. No other module owns or supplements this authority.

Before the session installs any import authority, it snapshots the complete
`sys.modules` mapping as exact name-to-object references and separately records
the complete key set. It enumerates every key equal to `orev3` or beginning
with `orev3.`, snapshots those entries by exact name and object reference, and
temporarily removes every one of them, including names outside the seven
governed names. No preexisting `orev3` module may satisfy a governed import.
During the session, the only permitted `orev3` keys are the four namespace
shells and three authenticated source modules named in this section. Appearance
of any other `orev3` key is a hard controller failure.

The project-code finder is the temporary identifier-specific
`ControllerPureClosureMetaPathFinder`, implemented only in
`src/orev3/execution/phase3b_components.py`. Its role begins only after guarded
import authorization: it resolves authenticated module specs, resolves the
four namespace shells, and provides defense-in-depth hard failure for an
unauthorized `orev3` request that reaches `sys.meta_path`.

During the governed session, `orev3`, `orev3.execution`, `orev3.features`, and
`orev3.experiments` are namespace-only package shells created by the finder.
Their `__path__` values are empty tuples, their loaders expose no source, and
no package `__init__.py` executes. The three tuple members are the only
source-backed project modules. For an exact mapped module request the finder
returns the governed spec and loader. For one of the four exact package names
it returns only the governed namespace-shell spec. For every other module name
equal to `orev3` or beginning with `orev3.`, it raises `ModuleNotFoundError`
immediately; it never returns `None` and never permits a later finder, ambient
`sys.path`, editable installation, or detached filesystem to resolve the
request.

The exact source loader is
`AuthenticatedControllerPureSourceLoader`, implemented only in
`src/orev3/execution/phase3b_components.py`. It receives the already
authenticated strict UTF-8 source bytes and one exact
`ControllerPureClosureMember`, rechecks that the bytes have the member's
SHA-256, compiles the bytes using the authenticated repository-relative path
as filename metadata only, and executes them in the requested governed module
namespace. It does not reopen a repository path, read a sibling, mutate
`sys.path`, or delegate to a standard file loader. UTF-8 decoding failure,
member/name mismatch, or source-byte mismatch rejects.

The loader executes each governed source module with a new controlled builtins
mapping formed from the interpreter builtins, with `open`, `breakpoint`,
`compile`, `eval`, `exec`, and `input` absent and with `__import__` replaced by
`controller_pure_guarded_import`, then exposed read-only through
`types.MappingProxyType`. The module's `__builtins__` entry must remain the
identical mapping proxy through import and validation. That function is
implemented only in
`src/orev3/execution/phase3b_components.py`. A governed module never receives
the ambient `builtins.__import__` directly and cannot replace the controlled
`__import__` entry. Direct import of `builtins`, `importlib`, `inspect`,
`pkgutil`, `runpy`, or another dynamic-loading facility is absent from the
tables below and therefore rejects. Invoking ambient import through an imported
helper is prohibited but is not prevented by the controlled builtins mapping
alone; the unresolved standard-library exposure boundary below must close that
route. Replacing `__builtins__["__import__"]` directly rejects because the
mapping is read-only, and dynamically executing module source remains
prohibited.

The requesting governed module name is authority-bearing. The exact permitted
project import-edge table is:

```text
orev3.execution.canonical
  -> ()
orev3.features.rq003_contracts
  -> ()
orev3.experiments.rq003_experiment5_configuration
  -> (
       orev3.execution.canonical,
       orev3.features.rq003_contracts,
     )
```

No relative project import is permitted. For every governed import call,
`controller_pure_guarded_import` obtains the requester from the governed
execution globals, rejects an absent or non-governed requester, resolves the
requested absolute name without aliasing or normalization, and checks the
exact requester-to-target edge before consulting or returning a session cache
entry. Thus an allowed or unauthorized target already in `sys.modules` cannot
bypass edge authorization. Every other `orev3` edge rejects before cache use.

The exact direct standard-library import-edge table is:

```text
orev3.execution.canonical
  -> (
       collections.abc,
       hashlib,
       json,
       pathlib,
       re,
       typing,
       unicodedata,
     )
orev3.features.rq003_contracts
  -> (
       collections.abc,
       dataclasses,
       enum,
       hashlib,
       json,
       math,
       re,
       struct,
       typing,
     )
orev3.experiments.rq003_experiment5_configuration
  -> (
       collections.abc,
       hashlib,
       typing,
     )
```

These exact names follow the tracked imports of `canonical.py` and
`rq003_contracts.py` and the frozen static validator design. The validator has
no direct `pathlib` edge and never receives `pathlib.Path`. Only
`orev3.execution.canonical` imports `pathlib`, and its authenticated tracked
source imports only `PurePosixPath` for lexical repository-path validation.
The prospective validator operates only on supplied authenticated bytes and
closed authority objects.

After a governed direct standard-library edge is authorized, that standard-
library module would execute under normal CPython import semantics. The current
design is not yet closed at this point: an ordinary CPython module object can
expose its ambient `__builtins__` mapping (including ambient `__import__`) and
other transitive module objects even when the governed caller's own
`__builtins__` value is a read-only controlled mapping. Returning ordinary
standard-library module objects would therefore permit recovery of import or
other capabilities outside the requester edge table. The controlled
`MappingProxyType` builtins model alone does not close that route.

**STANDARD-LIBRARY EXPOSURE GOVERNANCE PREREQUISITE REQUIRED.** This is a
separately governed successor prerequisite, not a prerequisite to adopting and
freezing this governance decision. This decision may be adopted while the
subordinate mechanism remains unresolved because the unresolved boundary is
explicit, implementation remains prohibited, and no implementation writer may
select that mechanism.

Before any dependent adapter-v4/readiness implementation may begin, the
successor governance decision must freeze one exact implementable standard-
library exposure mechanism that prevents this recovery. It must address exact
requester-specific exports, ordinary module-object ambient builtins,
`__import__` recovery, module globals and reflection, transitive modules,
cached modules, dynamic loading, filesystem/network/process/provider/outcome
capability, and conformance tests. That mechanism must preserve the exact
direct edge tables above, must not rely on source-review prose or on the
authenticated module being non-adversarial, and must prove that `builtins`,
ambient `__import__`, dynamic loading, filesystem, network, process, provider,
outcome, and third-party capabilities cannot be recovered through an allowed
helper. Until that separate prerequisite is adopted, frozen, and independently
verified, validator import/execution implementation is not authorized. A
requested module that is neither an exact authorized project edge nor an exact
authorized direct standard-library edge for that requester still rejects
before cache use or fallback.

The import session calls `_imp.acquire_lock()` immediately before the complete
`sys.modules` snapshot, requires `_imp.lock_held()` throughout the session, and
calls `_imp.release_lock()` only after cleanup verification completes; the same
session thread uses the lock's reentrant import behavior. Failure to acquire or
retain that lock is a hard controller failure. The session snapshots the exact
pre-session `sys.path` value and exact `sys.meta_path` object sequence. Its
complete `sys.modules` snapshot covers every direct standard-library module,
every preexisting transitive module later touched, and every unrelated module,
not only project names.

Installation order is exact:

1. authenticate all closure members from approved S;
2. construct the exact module-name mapping;
3. acquire the global import lock and snapshot the complete `sys.modules`
   key-to-object mapping and key set;
4. snapshot `sys.path` exactly;
5. snapshot the exact `sys.meta_path` object sequence;
6. remove every preexisting `orev3` and `orev3.*` entry;
7. construct namespace shells and guarded import-session authority;
8. install `ControllerPureClosureMetaPathFinder` at index zero;
9. import and execute the validator only through
   `AuthenticatedControllerPureSourceLoader` and controlled builtins; and
10. execute validation, then enter `finally` cleanup.

No validator code executes before Steps 1 through 8 complete. Nested or
concurrent `ControllerPureImportSession` instances reject instead of sharing
state.

Cleanup order in the unconditional `finally` boundary is exact:

1. prevent further governed imports;
2. remove `ControllerPureClosureMetaPathFinder`;
3. remove every session-created `orev3` entry;
4. remove every `sys.modules` entry created during the session that was absent
   from the complete pre-session key set, including newly loaded standard
   library modules;
5. restore every preexisting entry changed or removed to the identical
   pre-session object reference;
6. restore every original `orev3` entry exactly;
7. verify every original absence remains absent;
8. verify `sys.path` equals its exact pre-session value;
9. restore and verify the exact pre-session `sys.meta_path` object sequence;
10. verify that no finder, loader, guarded-import, namespace-shell, or session
    object remains installed globally; and
11. release the global import lock.

Replacement of any preexisting `sys.modules` entry outside the governed
`orev3` set is restored and is also a hard validation failure. Every unrelated
preexisting entry that was untouched remains the identical object. Cleanup or
restoration mismatch is a hard controller failure even when restoration
otherwise completes. The same cleanup runs after source decoding or
compilation failure, guarded-import rejection, partial namespace creation,
module execution failure, or validation failure. No partial session authority
survives. The validator remains `CONTROLLER_PURE` and receives only
authenticated bytes and closed authority objects.

## 11. Exact invocation stage

The configuration-resource validator is invoked during detached Phase-3A
Source-S prerequisite reconstruction, immediately after all three of:

1. adapter-v4 registry reference and descriptor authentication;
2. implementation-binding authentication; and
3. profile-contract reconstruction.

It completes before Phase-3B evidence preparation and before readiness
candidate construction. The same authentication function is rerun during
independent current-readiness/prerequisite reconstruction from the approved
source commit. Re-execution reconstructs authority; it does not grant new
authority or create a readiness lifecycle transition.

## 12. Closed validation request

The conceptual immutable type is
`ExperimentConfigurationResourceValidationRequest`. It contains exactly:

- `approved_source_commit`;
- `adapter_identifier`;
- `adapter_identity`;
- `configuration_resource`;
- `expected_experiment_configuration_identity`;
- `execution_profile_name`;
- `research_specification_profile_identity`; and
- `adapter_profile_contract_identity`.

`configuration_resource` is the exact closed object from Section 5.
`expected_experiment_configuration_identity` is the authenticated
implementation-binding value and must also equal the adapter sibling field
before validation succeeds. Repository access, schema registries, component
policies, Source-S scope declarations, and blob loaders are controller
authority, not request fields. No path, callback, opener, provider, or policy
override may enter the request.

## 13. Required validation operations

One governed controller authentication function must execute these operations
in order and fail closed on any error:

1. resolve `configuration_path` at approved S;
2. require a tracked safe regular `100644` blob;
3. authenticate its Git object identity, byte count, and SHA-256;
4. resolve `configuration_schema_path` at the same S and authenticate its safe
   blob, identifier, revision, Git object, byte count, and SHA-256;
5. reconstruct `configuration_schema_identity` by Section 8;
6. resolve the validator identifier through `COMPONENT_POLICIES` and
   `resolve_component` at the same S;
7. authenticate every validator field and component identity;
8. require configuration, schema, and validator paths in the exact governed
   Source-S scopes and roles from Section 17;
9. require canonical configuration bytes and validate their closed shape
   against the authenticated schema;
10. reconstruct the Experiment-specific configuration identity under the
    frozen Slice-3 formula;
11. reconstruct the Research Specification v2 profiled configuration identity
    using the authenticated Research Specification profile identity;
12. cross-check configuration protocol, source-processing, dataset, and both
    distinct profile materials against already authenticated authority;
13. compare the reconstructed profiled identity with the adapter sibling
    `experiment_configuration_identity`;
14. compare it with the implementation-binding
    `experiment_configuration_identity`;
15. reconstruct `configuration_resource_identity` over every resource field
    except only its claimed identity;
16. construct the authenticated result in Section 14; and
17. reject every substitution, stale object, cross-commit object, unknown
    field, unsupported revision, noncanonical byte sequence, or opaque matching
    claim.

The function must not validate one source commit while loading any resource or
component from another commit or the mutable working tree.

## 14. Closed authenticated result

The conceptual immutable result type is
`AuthenticatedExperimentConfigurationResource`. It contains exactly:

1. `schema_version`;
2. `approved_source_commit`;
3. `adapter_identifier`;
4. `adapter_identity`;
5. `configuration_resource_identity`;
6. `configuration_git_object_identity`;
7. `configuration_byte_count`;
8. `configuration_sha256`;
9. `configuration_schema_identity`;
10. `configuration_validator_component_identity`;
11. `experiment_specific_configuration_identity`;
12. `profiled_experiment_configuration_identity`; and
13. `authenticated_configuration_resource_identity`.

Its `schema_version` is exactly `1`. Its identity domain is exactly:

```text
orev3:readiness-authenticated-experiment-configuration-resource:v1\n
```

Identity reconstruction is:

```text
domain_identity(
  "orev3:readiness-authenticated-experiment-configuration-resource:v1\n",
  complete_result_without_only_authenticated_configuration_resource_identity
)
```

Every preceding result field participates. Only the claimed
`authenticated_configuration_resource_identity` is excluded.

## 15. Result status and readiness reconstruction

The authenticated result is immutable transient reconstruction authority. The
future implementation adds exactly this field to the existing frozen dataclass:

```text
ReadinessPrerequisiteContracts
  .authenticated_experiment_configuration_resource:
    AuthenticatedExperimentConfigurationResource | None = None
```

The field is the final dataclass field and its default is exactly `None`.
Existing positional and keyword constructors remain valid; no legacy caller
update is required solely to satisfy constructor arity. For
`ProspectiveRegistryGeneration.ADAPTER_V4_CONFIGURATION_RESOURCE`, the field
must be supplied explicitly after successful authentication and contains the
exact reconstructed result from Section 14. A v4 constructor path that omits
the field and therefore receives default `None`, or that explicitly supplies
`None`, fails closed. For every existing generation (`PHASE2`, `PHASE3A`,
`PHASE3B`, and `READINESS_V1_1`), the field remains exactly `None`; an explicit
legacy non-null value rejects. No alternate constructor behavior, absence
sentinel, alternate result carrier, or identity-only value is permitted.
Current-readiness validation reconstructs and compares the complete non-null
result for the v4 generation.

`ReadinessPrerequisiteContracts` is a transient frozen Python authority object.
Current authority defines no serialized prerequisite-contract identity or
identity domain over its dataclass fields. Adding this field therefore changes
no prerequisite-contract identity. It also changes no readiness-record-v2
material, identity formula, schema field, lifecycle state, or evidence kind.

The result is not a readiness evidence kind, readiness-record field, execution
artifact, scientific output, Source S declaration, or execution capability.

## 16. Readiness-record and implementation-binding dispositions

### 16.1 Readiness record

**NO NEW READINESS-RECORD FIELD REQUIRED.**

Readiness-record v2 already binds source commit, adapter identity, registry
identity, profiled experiment configuration identity, and implementation
binding. Adapter-v4 identity transitively binds the complete resource object.
Independent readiness can reload adapter-v4 from S, reconstruct every resource
and component byte identity, and reproduce the authenticated result. Adding a
duplicate readiness-record equality surface is prohibited.

### 16.2 Implementation binding

**NO IMPLEMENTATION-BINDING SCHEMA REVISION REQUIRED.**

The required equality is:

```text
implementation_binding.experiment_configuration_identity
== adapter.configuration.experiment_configuration_identity
== adapter.configuration.experiment_configuration_resource
     .profiled_experiment_configuration_identity
== authenticated_configuration_resource
     .profiled_experiment_configuration_identity
```

The implementation binding must not duplicate configuration resource path,
blob, schema, validator, or resource identity authority.

## 17. Profile identity distinction and Source-S scope roles

The Research Specification v2 profile identity is distinct from the adapter
six-contract profile-binding identity:

```text
research_specification_profile_identity
!= adapter_profile_contract_identity
```

The first reconstructs `ProfiledExperimentConfiguration`. The implementation
binding’s `profile_identity` remains the adapter six-contract identity. Neither
may substitute for the other.

Adapter-v4 `governed_scope_paths` must list all three exact resource paths:

- `config/research/readiness/experiments/rq003-experiment-005-configuration-v1.json`;
- `src/orev3/execution/schemas/v1/rq003-experiment-005-configuration.schema.json`;
  and
- `src/orev3/experiments/rq003_experiment5_configuration.py`.

That descriptor membership is distinct from Source-S scope-role authority.
The Source-S declarations bind roles exactly as follows:

- the configuration path has its own exact top-level `configuration` scope;
- the configuration schema is contained in and authenticated by the existing
  singleton `readiness_schema` scope at
  `src/orev3/execution/schemas/v1`; it does not create a second
  `readiness_schema` declaration; and
- the validator path has an exact `control_plane` scope with nesting `nested`
  and `parent_path: "src/orev3"`, under the existing `source_tree` parent at
  `src/orev3`.

Omission from `governed_scope_paths`, absence of the configuration scope,
absence of the singleton schema parent, a second `readiness_schema` scope,
wrong validator role/nesting/parent, or ambiguous overlapping authority
rejects.

## 18. Exact Source-S reconstruction order

Future reconstruction follows exactly:

1. resolve approved S;
2. select the explicit v4 schema overlay;
3. authenticate registry bytes and reconstruct registry identity;
4. select the exact adapter descriptor reference from the authenticated
   registry;
5. authenticate descriptor bytes and reconstruct adapter-v4 identity;
6. compare descriptor SHA-256 and adapter identity with the authenticated
   registry reference;
7. resolve configuration, schema, and validator paths from the same S and
   require their governed scopes and safe regular blob modes;
8. authenticate configuration/schema/validator Git objects, byte counts where
   declared, and SHA-256 values;
9. resolve and authenticate the validator through the finite component policy;
10. reconstruct schema identity, validate canonical configuration bytes, and
    reconstruct Experiment-specific, profiled, and configuration-resource
    identities;
11. cross-check implementation-binding and both profile identities;
12. construct `AuthenticatedExperimentConfigurationResource`; and
13. continue ordinary readiness prerequisite reconstruction.

No later step may supply authority needed by an earlier step.

## 19. Identity dependency DAG

The identity order is acyclic and exact:

```text
approved S
  -> registry bytes / registry identity
  -> descriptor reference
  -> descriptor bytes
  -> configuration/schema/validator blobs
  -> validator component identity
  -> configuration-schema identity
  -> Experiment-specific configuration identity
  -> Research Specification v2 profiled configuration identity
  -> configuration-resource identity
  -> adapter-v4 identity / authenticated registry-reference equality
  -> implementation-binding equality
  -> authenticated-resource identity
  -> ReadinessPrerequisiteContracts
  -> readiness reconstruction
```

Registry bytes and registry identity are authenticated before descriptor
selection. The registry reference supplies the expected descriptor SHA-256 and
adapter identity. Descriptor parsing calculates the claimed adapter identity
at Step 5 so the registry reference can be checked, but that identity is not
accepted as complete adapter authority until the resource identity and all
resource bytes independently reconstruct at the later DAG equality node. No
registry identity is constructed after adapter reconstruction. No reverse
dependency or coordinated resealing is permitted.

This cryptographic identity DAG is unchanged. Its implementation is governed
by the separate authority sequence:

```text
narrow readiness/adapter governance
  -> standard-library exposure governance
  -> adapter-v4/readiness implementation
```

The second node is mandatory authority before implementation and is not an
identity input or reverse dependency in the cryptographic DAG.

## 20. Schema overlays and backward compatibility

Adapter declaration v1, v2, and v3 remain immutable. Existing
generation identifiers and serialized values remain unchanged. Historical and
prospective-v1.1 fixtures continue selecting their existing generation enum
members and overlays; their
`ReadinessPrerequisiteContracts.authenticated_experiment_configuration_resource`
value is exactly `None`.

Only `ADAPTER_V4_CONFIGURATION_RESOURCE`, serialized as
`prospective-v1.1-adapter-v4-configuration-resource`, selects adapter-v4 and
requires a non-null authenticated resource result. Selection is explicit at
the detached Phase-3A request, Phase-3B request, prerequisite loader, and
`CurrentReadinessInput`. There is no implicit newest-revision lookup, ambient
default to v4, cross-generation retry, or inference from descriptor bytes.

Each overlay contains one `adapter-declaration` semantic kind. V3 and v4 may
not simultaneously occupy that kind in one overlay or registry generation.
V4 requires `experiment_configuration_resource`; legacy absence is accepted
only by an explicitly governed older adapter revision.

Existing governed overlay member counts remain exactly 10, 20, and 29 where
those generations currently require them. A prospective v4 overlay replaces
the single adapter-declaration schema member for the same semantic kind; it
does not append a second kind and therefore does not change those counts.

## 21. Failure and substitution matrix

Every future implementation and test surface must fail closed on at least:

- resource `schema_version` substitution;
- configuration identifier substitution;
- configuration revision substitution;
- configuration path substitution;
- identical configuration bytes claimed under a different path;
- configuration Git-object substitution;
- configuration byte-count substitution;
- configuration SHA-256 substitution;
- schema identifier substitution;
- schema revision substitution;
- schema path substitution;
- identical schema bytes claimed under a different path;
- schema Git-object substitution;
- schema byte-count substitution;
- schema SHA-256 substitution;
- schema identity substitution;
- noncanonical configuration JSON;
- noncanonical schema JSON;
- unsupported schema material or keyword;
- non-blob resource object;
- tree object at a resource path;
- symlink-like or other non-regular representation;
- executable or other non-`100644` mode;
- validator identifier substitution;
- validator revision substitution;
- validator path substitution;
- validator Git-object substitution;
- validator SHA-256 substitution;
- validator worker-kind substitution;
- validator component-identity substitution;
- validator dependency or capability-closure substitution;
- unregistered validator selection;
- descriptor-selected arbitrary module, callable, or validator;
- Experiment-specific identity resealing;
- profiled identity resealing;
- configuration-resource identity resealing;
- authenticated-result identity resealing;
- coordinated descriptor/configuration/schema substitution;
- implementation-binding identity mismatch;
- Research Specification profile / adapter profile substitution;
- `execution_profile_name` / Research Specification profile identity mismatch;
- governed-scope omission;
- wrong scope role;
- stale Source-S object;
- cross-commit resource or component object;
- v4 descriptor under a v3 overlay;
- v3 descriptor under a v4 overlay;
- v4-to-v3 downgrade at the detached Phase-3A request;
- v4-to-v3 downgrade at the Phase-3B request or sibling handoff;
- v4-to-v3 downgrade at prerequisite loading;
- v4-to-v3 downgrade at current-readiness reconstruction;
- unknown `ProspectiveRegistryGeneration` value;
- unknown `PreparationAuthorityGeneration` value;
- unknown `EvidenceAuthorityGeneration` value;
- direct schema-policy overlay substitution;
- direct document-policy overlay substitution;
- coordinated generation-to-policy and generation-to-document-policy map
  substitution;
- v4 final/current-readiness generation paired with legacy Phase-3A;
- v4 final/current-readiness generation paired with legacy Phase-3B;
- legacy final/current-readiness generation paired with v4 Phase-3A;
- legacy final/current-readiness generation paired with v4 Phase-3B;
- v4 Phase-3A paired with legacy Phase-3B;
- legacy Phase-3A paired with v4 Phase-3B;
- sibling handoff generation mismatch;
- request generation differing from loader generation;
- simultaneous v3/v4 same-kind membership;
- retry under another generation after unknown/rejected generation;
- ambient/default selection replacing an explicitly supplied v4 generation;
- transient `AuthenticatedExperimentConfigurationResource` substitution during
  prerequisite construction or current-readiness reuse; and
- outcome- or provider-capable dependency entering the pure validator closure.

Coordinated mutation of claims must reject when independently reconstructed
committed authority differs. Direct policy tests must independently mutate the
registry schema-policy constant, document-policy constant,
generation-to-policy map, and generation-to-document-policy map. Both isolated
and coordinated substitutions must reject; end-to-end rejection alone is
insufficient evidence for these bindings.

## 22. Prospective implementation path scope

This is the exact bounded prospective implementation surface. It does not
authorize modification.

### 22.1 Existing production paths

| Path | Exact prospective responsibility |
| --- | --- |
| `src/orev3/execution/readiness_record.py` | define the six v4 Phase-3A/Phase-3B/final overlay constants and their document bindings only; readiness-record v2 schema, fields, identity, and evidence kinds do not change |
| `src/orev3/execution/registry.py` | recognize schema version 4 after schema validation and apply v3-equivalent external-input semantics plus mandatory resource placement; registry schema and identity domain do not change |
| `src/orev3/execution/phase3b_components.py` | add the one finite `CONTROLLER_PURE` validator policy, `CONTROLLER_PURE_COMPONENT_CLOSURES`, frozen member/resolver types, `resolve_controller_pure_component_closure`, `ControllerPureImportSession`, `controller_pure_guarded_import`, `ControllerPureClosureMetaPathFinder`, and `AuthenticatedControllerPureSourceLoader`; no other path owns import-session machinery |
| `src/orev3/execution/readiness_contracts.py` | add the exact generation, authenticated request/result reconstruction, v4 schema-policy selection, exact Source-S role checks, and required dataclass field |
| `src/orev3/execution/preparation.py` | add the matching Phase-3A generation, select the v4 Phase-3A overlay, add exact resource objects/scopes, and invoke resource authentication in detached prerequisite preparation |
| `src/orev3/execution/evidence_preparation.py` | add the matching Phase-3B generation and explicit v4 Phase-3A/Phase-3B generation handoff and overlay selection |
| `src/orev3/execution/evidence_preparation_worker.py` | dispatch only the exact v4 generation to the v4 Phase-3B overlay and unchanged-value Phase-3A sibling request |
| `src/orev3/execution/detached_evidence.py` | reconstruct the exact v4 Phase-3A command/result generation value during detached evidence validation |
| `src/orev3/execution/readiness_candidate.py` | accept and reconstruct the exact v4 Phase-3A generation in candidate-side detached-evidence checks without adding a readiness field |
| `src/orev3/execution/current_readiness.py` | add the explicit generation input, select the v4 final overlay, and rerun/compare the authenticated resource during prerequisite reconstruction |
| `src/orev3/execution/git_state.py` | consume the selected governed generation during independent readiness-v2 Git binding reconstruction, select its exact policy/document-policy overlay, accept adapter-v4 only for `ADAPTER_V4_CONFIGURATION_RESOURCE`, preserve adapter-v3 for every legacy generation, reject generation/schema mismatch, and independently reconstruct registry/descriptor/configuration-resource authority |

`readiness_record.py` appears solely because it owns governed schema-generation
and document-policy constants. Its modification is implementation
infrastructure, not a readiness-record schema revision. No readiness-record
field, identity material, lifecycle state, or evidence kind is added.

The authenticated resource result does not cross into an INPUT_PROJECTOR,
REPLAY_PREPARATION, or READINESS_TEST worker request and is not Phase-3B
evidence. The two evidence-preparation paths above change only explicit
generation/overlay dispatch and the Phase-3A sibling handoff. No projection,
Replay, or input-worker path is in scope.

The `git_state.py` modification is reconstruction infrastructure only. It adds
no readiness-record field, evidence kind, lifecycle state, or readiness-record
identity material. `readiness_candidate.py` is limited to the generation check
listed above. Every readiness-record schema file remains excluded, and the
generic Git object primitives and existing readiness-record semantics are
reused.

### 22.2 New production paths

- `src/orev3/execution/schemas/v1/adapter-declaration-v4.schema.json`;
- `src/orev3/experiments/rq003_experiment5_configuration.py`; and
- `src/orev3/execution/schemas/v1/rq003-experiment-005-configuration.schema.json`.

### 22.3 Exact test paths

| Test path | Required coverage |
| --- | --- |
| `tests/execution/test_experiment_configuration_resource.py` | request/result/resource identities, resource authentication, complete resource/substitution matrix, exact finite closure authentication, and transient-result identity/source/adapter/configuration substitutions |
| `tests/experiments/test_rq003_experiment5_configuration.py` | closed configuration schema, canonical bytes, Experiment-specific and profiled identity reconstruction |
| `tests/execution/test_phase3a_preparation.py` | exact Phase-3A generation, adapter-v4 schema/registry loader path, resource scopes, detached request, unknown generation, downgrade, and direct Phase-3A policy/document-policy substitution |
| `tests/execution/test_phase3b_authority.py` | exact Phase-3B generation/overlay and unchanged-value sibling handoff; finite `CONTROLLER_PURE_COMPONENT_CLOSURES` membership/order/blob authentication; missing/extra/substituted and forbidden-capability dependencies; exact project/stdlib import edges, cache-before-authorization rejection, guarded builtins, complete cache-delta restoration, and import-session cleanup on success and every failure point |
| `tests/execution/test_phase3b_integration.py` | explicit v4 detached boundary: preserve the exact v4 EvidenceAuthorityGeneration, hand the matching v4 PreparationAuthorityGeneration to Phase-3A, use the v4 overlay at both stages, produce the non-null authenticated configuration-resource prerequisite result, and complete successfully without legacy fallback; reject v4 Phase-3B with a legacy Phase-3A sibling, legacy Phase-3B with a v4 sibling, unknown or mutated generation, and every fallback attempt; exercise the governed import session at the actual detached boundary without adding a production test hook |
| `tests/execution/test_phase3c_readiness_contracts.py` | v4 final overlay, exact final dataclass field/default, legacy `None`, legacy non-null rejection, v4 non-null requirement, exact reconstructed-result acceptance, transient-result substitutions, registry-first reconstruction, and corrected scope roles |
| `tests/execution/test_phase3c_readiness_record_v2.py` | unchanged readiness-record v2 schema/identity and exact 10/20/29 counts; `git_state.py` v4 Git binding reconstruction; legacy-v3 preservation; v3-only behavior relaxed only for the governed v4 generation; schema-policy, document-policy, map, cross-stage mismatch, and unknown-generation rejection |
| `tests/execution/test_phase3c_readiness_candidate.py` | v4 detached-generation reconstruction with no new readiness field/evidence kind |
| `tests/execution/test_phase3c_current_readiness.py` | explicit current generation; authenticated-result rerun/comparison; final/Phase-3A/Phase-3B mismatch; request/loader mismatch; downgrade, fallback, ambient-default, cross-generation, and transient-result rejection |

No other production or test path belongs to this prospective implementation
surface. A later finding that another path is necessary is a governance stop,
not permission to expand this list. This section creates no implementation,
adapter, registry, Source-S, readiness, or execution authority.

Production paths explicitly excluded include every readiness-record schema
file, projection code, Replay code, `input_projection_worker.py`, Experiment
005 ranking/evaluation code, provider/backend code, and outcome-gate provenance
code.

## 23. Mandatory future conformance tests

Positive conformance must prove:

- adapter-v4 schema selection and closed validation;
- adapter identity reconstruction;
- configuration-resource identity reconstruction;
- exact configuration path/blob/object/count/SHA authentication;
- exact schema path/blob/object/count/SHA/identity authentication;
- finite validator component reconstruction;
- Experiment-specific identity reconstruction;
- profiled identity reconstruction;
- adapter sibling equality;
- implementation-binding equality;
- detached Phase-3A reconstruction;
- independent current-readiness reconstruction;
- exact Source-S scope roles;
- v1/v2/v3 backward compatibility;
- explicit v4 overlay selection; and
- unchanged governed schema-registry member counts.

Negative conformance must exercise every item in Section 21, including
coordinated substitutions rather than only isolated mismatches. Tests must also
prove the validator closure lacks outcome, evaluation, provider, network,
allocation, wallet, transaction, and arbitrary filesystem capability.

Closure-escape tests must additionally reject a preloaded forged validator,
a preloaded forged canonical or RQ-003 helper, an ambient module with the same
name, an unauthorized `orev3` import, a fallback finder that could otherwise
provide an unauthorized project module, a package initializer outside the
tuple, every third-party import, a source-loader filesystem reopen, any
`sys.path` mutation, a finder left installed after failure, a governed module
left cached after success or failure, and any restoration mismatch. Success
and every injected failure point must prove exact restoration of the original
module-object references, absences, `sys.path`, and `sys.meta_path`.

Import/cache tests must also cover a preloaded `orev3.unauthorized`, a
preloaded `orev3.execution.unauthorized`, a forged allowed module, a forged
namespace parent, an authorized target cached before edge authorization,
validator-direct `pathlib`, validator-direct `builtins`, `importlib`, a
third-party module, an unauthorized edge to the other authenticated helper, an
ambient cached dynamic-loader module, replacement of a preexisting unrelated
module, and partial import failure. Each case must establish the expected hard
rejection plus complete `sys.modules` delta, `sys.path`, and `sys.meta_path`
restoration. Success and failure must leave no finder, loader, guarded-import,
namespace-shell, or session object globally reachable through import state.

Transient prerequisite-result tests must establish exactly:

- a legacy constructor default is `None`;
- an explicit legacy non-null result rejects;
- a v4 default or explicit `None` rejects;
- the exact reconstructed v4 result passes;
- authenticated-result identity substitution rejects;
- approved-source substitution rejects;
- adapter identity substitution rejects;
- configuration-resource identity substitution rejects;
- Experiment-specific identity substitution rejects;
- profiled identity substitution rejects;
- a result from another generation rejects; and
- a result from another source commit rejects.

Generation/overlay unit tests must independently mutate each schema-policy
constant, document-policy constant, generation-to-policy map, and
generation-to-document-policy map, and must exercise every cross-stage pairing
and unknown enum value in Section 21. They must prove that no rejected or
unknown value is retried under another generation and no explicit v4 value is
replaced by a default.

## 24. Forbidden semantic and authority scope

This prospective revision must not change:

- Experiment 005 scientific semantics;
- source selection or dataset membership;
- the pre-/post-outcome boundary;
- readiness lifecycle states;
- readiness evidence kinds;
- readiness-record v2 schema;
- implementation-binding schema;
- provider or backend authority;
- attempt allocation or control storage;
- execution records or execution authority;
- a production adapter instance;
- production registry membership;
- final Source S;
- the thin Experiment 005 execution entry point;
- the subordinate outcome-gate provenance interface;
- outcome access or evaluation;
- confirmation-dataset selection;
- Strategy or Paper Miner work;
- wallets, transactions, capital, or SOL.

This decision does not authorize implementation of any prospective path in
Section 22 and does not authorize creation of the Experiment 005 configuration
bytes.

## 25. Authority disposition

**NARROW ADAPTER/READINESS REVISION SUFFICIENT.**

The minimum prospective revision category is exactly:

**ADAPTER SCHEMA + READINESS VALIDATION IMPLEMENTATION**

It requires adapter declaration v4, finite component registration, and
readiness/prerequisite reconstruction changes described here. It does not
require:

- a readiness-record schema revision;
- a readiness evidence-kind revision;
- an implementation-binding schema revision; or
- a broad Execution Readiness specification revision.

This disposition does not assert that implementation already exists.

## 26. Successor order and non-authorization

This governance decision is adopted and frozen before the separate
standard-library exposure mechanism is resolved. Its adoption freezes design
authority only and authorizes no implementation. The required sequence is
exactly:

```text
status-only adoption/freeze of this governance document
  -> one-path commit and normal push
  -> independent parent/path/byte/semantic/remote verification
  -> bounded governance design of the standard-library exposure prerequisite
  -> independent review
  -> status-only adoption/freeze of that prerequisite
  -> independent exact-byte and remote verification
  -> only then bounded adapter-v4/readiness implementation authorization
```

No implementation writer is permissible before the standard-library exposure
prerequisite is frozen and independently verified. Adoption of this document
does not authorize edits to `src/orev3/execution/phase3b_components.py`, the
adapter-v4 schema, the configuration validator, readiness/runtime code, the
standard-library exposure mechanism, tests, or any other production path.

Separately, the frozen Slice-3 prerequisite continues to require:

**SUBORDINATE OUTCOME-GATE PROVENANCE INTERFACE REQUIRED.**

That is a separate governance boundary. This decision neither defines nor
implements it. Neither successor task grants adapter adoption, registry
membership, Source S, readiness evidence, execution, or outcome access without
its own later authority.

## 27. Explicit non-authorizations

This decision creates no authority for:

- adapter-v4 or validator implementation;
- readiness/runtime/test modification;
- Experiment 005 configuration creation;
- production adapter creation or adoption;
- registry modification;
- final Source S;
- readiness evidence, candidate, READINESS_VALIDATED, E, R, or
  EXECUTION_READY;
- provider/backend, allocation, namespace, or control authority;
- STARTED or any experiment/ranking execution;
- outcome location, opening, parsing, authorization, or evaluation;
- the subordinate outcome-gate provenance task;
- confirmation-dataset selection;
- Strategy or Paper Miner work; or
- wallet, transaction, capital, or SOL access or use.

This decision is adopted and frozen prospectively. It authorizes no
implementation step; no implementation step is self-authorized.
