# RQ-003 Experiment 005 CONTROLLER_PURE Standard-Library Exposure Prerequisite v1

- Type: Prospective subordinate controller capability governance decision
- State: Adopted and frozen prospectively
- Experiment: `rq003-experiment-005-signed-share-imbalance-predictive-evaluation`
- Decision revision: `rq003-experiment-005-controller-pure-stdlib-exposure-prerequisite-v1`
- Scientific disposition: `SCIENTIFICALLY COMPATIBLE`
- Readiness disposition: `NARROW ADAPTER/READINESS REVISION SUFFICIENT`
- Standard-library exposure implementation authorized: No
- Adapter-v4/readiness implementation authorized: No
- Source S established: No
- Execution authorized: No
- Outcome access authorized: No

## 1. Purpose and controlling authority

This decision prospectively freezes the structural capability boundary for the
Experiment 005 `CONTROLLER_PURE` configuration validator. It does not implement
that boundary.

The following adopted decisions remain controlling:

- `docs/research/governance/rq003-experiment-005-slice3-authority-prerequisite-v1.md`,
  SHA-256
  `d3e8748c63f0a870a3b1e1439fa73ada0145c7502bccc8fd834987e8fb29a36e`;
  and
- `docs/research/governance/rq003-experiment-005-configuration-resource-readiness-revision-v1.md`,
  SHA-256
  `1183ccce903b96fc2c49dccc6cd59a78ff1c75c7aefe489350f49806cc7a6658`.

This decision preserves their adapter-v4 generation, configuration-resource
shape and identities, validator identifier/revision/path/worker kind, detached
Phase-3A validation stage, authenticated result, readiness-record and
implementation-binding dispositions, Source-S scope model, registry order,
production/test path sets, scientific semantics, and downstream
non-authorizations. It replaces only the unsafe assumption that the validator
path and reflective helper modules must execute as governed Python code.

## 2. Verified structural failure

The first verified recovery chain remains:

```text
ordinary allowed standard-library module object
  -> module globals / module.__builtins__
  -> ambient builtins.__import__
  -> ambient capability
```

A caller-controlled `__builtins__` mapping does not close this route.

The second-order failure is broader. Python-level wrappers, callable instances,
classes, metaclasses, descriptors, generated methods, exceptions, and bound
methods themselves form reflective object graphs. A representative forbidden
recovery from the previously proposed dataclass exposure is:

```text
generated_class.__init__.__globals__["__builtins__"]["__import__"]
```

Equivalent recovery may pass through function globals, closures, class
dictionaries, MRO/subclass traversal, Enum metaclasses, bound-method
`__func__`/`__self__`, reduction hooks, exception tracebacks, frames, or cached
module objects. Hiding selected attribute syntax does not remove those
capabilities. Authenticated source bytes, source review, a meta-path finder,
controlled builtins, AST filtering, and bytecode filtering do not make an
inherently reflective object safe to hand to governed Python code.

## 3. Architectural decision

The selected direction is:

**MODEL A — PURPOSE-BUILT PURE VALIDATOR WITH A NON-EXECUTED DECLARATIVE
COMPONENT.**

There is no governed Python execution for configuration validation. The frozen
validator path remains the authenticated component resource, but its bytes are
a closed declarative specification. They are never imported as a module, never
compiled, never passed to `exec` or `eval`, and never allowed to create a
function, class, exception, traceback, frame, descriptor, module, or callable
object.

Trusted controller code authenticates the component bytes, decodes the exact
inert specification, receives only authenticated configuration/schema bytes and
closed authority objects, performs the fixed operation sequence, and returns
only the existing authenticated result or a closed inert failure record. Input
data has no callback, code, object hook, provider, outcome, filesystem, network,
or process capability.

This is structural isolation: the governed side consists only of canonical
JSON-compatible scalar/container material. It cannot reflect into controller
functions because no controller function, module, class, exception, traceback,
frame, or descriptor crosses the data boundary.

## 4. Rejected architecture

**MODEL B — STRONGER ISOLATED EXECUTION BOUNDARY** is not selected.

A new Python process or sandbox would still contain reflective Python objects
and would require new normative authority for interpreter startup, environment
scrubbing, standard-library visibility, inherited descriptors, filesystem and
temporary-directory policy, IPC framing, process creation, sandbox profiles,
timeouts, signals, output capture, and cleanup. OS denial of side effects would
not itself prevent recovery of in-process `sys`, `builtins`, import machinery,
frames, or module objects. That substantially broader mechanism is unnecessary
because configuration validation can be expressed as a closed inert-data
operation without executing governed code.

The existing detached readiness boundary remains intact; it is not promoted
into a new security sandbox or provider authority by this decision.

## 5. Exact declarative validator resource

The prospective component coordinates remain exactly:

| Field | Value |
| --- | --- |
| Identifier | `rq003-experiment-005-configuration-validator-v1` |
| Revision | `1` |
| Path | `src/orev3/experiments/rq003_experiment5_configuration.py` |
| Worker kind | `CONTROLLER_PURE` |

The file is not an executable module. Its complete bytes have exactly this
form:

```text
CONTROLLER_PURE_VALIDATOR_SPEC = <canonical JSON object followed by LF>
```

The prefix is the exact ASCII byte string
`CONTROLLER_PURE_VALIDATOR_SPEC = `, including one trailing space. The suffix is
the existing readiness canonical JSON encoding of the following complete
closed object, including its terminal LF:

```json
{
  "engine_identifier": "rq003-experiment-005-configuration-validation-engine-v1",
  "operation_identifiers": [
    "strict-readiness-json-parse-v1",
    "rq003-experiment-005-configuration-schema-validate-v1",
    "rq003-canonical-encoding-parity-v1",
    "rq003-experiment-005-specific-configuration-identity-v1",
    "research-specification-v2-profiled-configuration-identity-v1",
    "configuration-authority-cross-check-v1"
  ],
  "schema_version": 1,
  "validator_identifier": "rq003-experiment-005-configuration-validator-v1",
  "validator_revision": 1
}
```

The displayed indentation is explanatory. Authoritative bytes are the fixed
prefix plus the existing canonical encoder's compact, sorted-key,
newline-terminated encoding. No comment, docstring, second statement, import,
call, name reference, annotation, function, lambda, class, comprehension,
generator, exception construct, or trailing byte is permitted.

## 6. Exact declarative decoding

`src/orev3/execution/phase3b_components.py` owns these prospective names:

- `CONTROLLER_PURE_DECLARATIVE_VALIDATOR_PREFIX`;
- `CONTROLLER_PURE_DECLARATIVE_VALIDATOR_SPECS`;
- `CONTROLLER_PURE_DECLARATIVE_VALIDATION_ENGINES`;
- `ControllerPureDeclarativeValidatorSpec`;
- `parse_controller_pure_declarative_validator_spec`;
- `validate_controller_pure_declarative_validator_binding`; and
- `execute_controller_pure_configuration_validation`.

`CONTROLLER_PURE_DECLARATIVE_VALIDATOR_SPECS` is a closed mapping containing
only the validator identifier and the exact semantic object in Section 5.

The parser accepts already authenticated strict UTF-8 bytes and performs only:

1. require the exact prefix at byte zero;
2. pass all remaining bytes, including the terminal LF, to the existing strict
   readiness canonical JSON parser;
3. reconstruct the remaining bytes with the existing readiness canonical JSON
   encoder and require byte equality;
4. require the decoded value to equal the mapping's exact closed object; and
5. return a frozen controller-owned
   `ControllerPureDeclarativeValidatorSpec` containing only copied immutable
   strings, integer revision, and operation tuple.

It does not call `ast`, `compile`, `eval`, `exec`, `runpy`, `importlib`, a source
loader, a module finder, or Python import machinery. It never constructs a
module namespace. The returned controller object is internal trusted control
state and is never provided to governed input.

## 7. Exact validation engine

`execute_controller_pure_configuration_validation` is trusted controller code
in `src/orev3/execution/phase3b_components.py`. It accepts only the already
frozen `ExperimentConfigurationResourceValidationRequest`, authenticated
configuration/schema bytes resolved at approved S, the independently resolved
validator binding, and the parsed declarative spec.

`CONTROLLER_PURE_DECLARATIVE_VALIDATION_ENGINES` is a closed mapping with the
single key `rq003-experiment-005-configuration-validation-engine-v1` and the
single internal controller target
`execute_controller_pure_configuration_validation`. The mapping and target are
loaded only from `phase3b_components.py` at the same approved S. That path must
be an authenticated safe regular `100644` `control_plane` blob already bound by
the approved source commit and readiness controller authority. Neither the
request, adapter, configuration, schema, nor declarative resource supplies a
callable, path, module, override, or alternate engine. Independent current
readiness reruns the same mapping from the same approved S. No new resource or
readiness-record identity field is introduced.

It performs the six operation identifiers exactly in listed order:

1. parse configuration bytes with existing strict readiness canonical JSON;
2. validate them against the authenticated Experiment 005 configuration schema
   using the existing closed readiness schema validator;
3. reconstruct the exact RQ-003 canonical encoding envelope defined by
   `orev3.features.rq003_contracts:canonical_encode` over inert supported
   values;
4. reconstruct the Experiment-specific configuration identity exactly as
   frozen by the Slice-3 prerequisite;
5. reconstruct the Research Specification v2 profiled configuration identity;
   and
6. perform every protocol/source-processing/profile/resource/adapter/
   implementation-binding equality frozen by the configuration-resource
   governance decision.

No operation is selected by configuration bytes, descriptor bytes, request
data, callback, module name, or runtime discovery. Unknown, missing, extra,
duplicated, or reordered operation identifiers reject before validation.

The RQ-003 canonical envelope implementation here is limited to the exact
identity-compatible scalar/container types required by Experiment 005
configuration material. It duplicates no measurement, ranking, evaluation,
metric, fold, bootstrap, inference, disposition, or confirmation formula. Its
bytes must be parity-tested against the frozen existing
`rq003_contracts.canonical_encode` implementation for every supported value and
all configuration identity material.

## 8. Repository/runtime closure

The governed component closure is replaced with this exact ordered tuple:

```text
(
  "src/orev3/experiments/rq003_experiment5_configuration.py",
)
```

That sole member is needed to bind the validator identifier to committed
reviewed bytes. It provides no runtime capability because it is never compiled
or executed and can decode only to the exact inert specification in Section 5.

These prior members are removed from the governed runtime closure:

- `src/orev3/execution/canonical.py`; and
- `src/orev3/features/rq003_contracts.py`.

`canonical.py` remains unchanged trusted controller infrastructure imported by
ordinary readiness controller code. It is not returned, exposed, or referenced
from governed input. `rq003_contracts.py` remains unchanged and outside the
production validation runtime; it is an independent parity oracle in tests
only. Neither helper is imported by, referenced from, or reachable through the
declarative validator resource.

The existing `CONTROLLER_PURE_COMPONENT_CLOSURES` mapping remains the binding
location, but its value for
`rq003-experiment-005-configuration-validator-v1` is the one-member tuple above.
The existing resolver continues to authenticate path, safe regular `100644`
blob mode, Git object identity, SHA-256, exact order, and Source-S scope.

## 9. Dataclass and Enum disposition

Dataclass and Enum machinery is absent from the governed runtime. The validator
specification contains only inert JSON-compatible material. It defines no
class, dataclass, Enum, decorator, generated method, metaclass, descriptor, or
instance.

`rq003_contracts.py` may construct its existing dataclasses and Enum only in
ordinary trusted test execution for parity comparison. Those objects never
enter the detached validation request, declarative spec, validation engine
input, authenticated result, or failure response.

## 10. Exception and traceback disposition

No controller Python exception object crosses the validation boundary. Trusted
controller code catches every parsing, schema, identity, authority, and
unexpected internal exception before constructing an external result. It must
not serialize `str(exc)`, `repr(exc)`, exception type/module, args, cause,
context, traceback, frame, stack, locals, globals, source line, or controller
path.

Failure is the following exact canonical JSON-compatible material:

```text
ControllerPureConfigurationValidationFailure
```

with exactly these fields:

- `schema_version`, exact integer `1`;
- `status`, exact string `rejected`;
- `failure_code`;
- `approved_source_commit`;
- `adapter_identifier`;
- `adapter_identity`;
- `configuration_resource_identity`;
- `configuration_validator_component_identity`; and
- `failure_identity`.

`failure_code` is exactly one of:

- `invalid_declarative_validator_spec`;
- `validator_authority_mismatch`;
- `invalid_configuration_resource`;
- `invalid_configuration_bytes`;
- `configuration_schema_rejected`;
- `experiment_configuration_identity_mismatch`;
- `profiled_configuration_identity_mismatch`;
- `authority_cross_check_failed`; or
- `controller_internal_failure`.

`failure_identity` is reconstructed with domain:

```text
orev3:readiness-controller-pure-configuration-validation-failure:v1\n
```

over the complete failure material excluding only `failure_identity`. The
failure contains no free-form diagnostic. The existing detached controller may
map it to its existing fail-closed outer status; this decision creates no new
readiness evidence kind or readiness-record field.

Success returns only the already frozen
`AuthenticatedExperimentConfigurationResource`. No intermediate Python object
or exception is returned.

## 11. AST and bytecode disposition

AST and recursive bytecode filtering are removed as capability-isolation
authority. The validator component is never compiled, so no validator bytecode
exists.

Tests may parse the component with `ast` as a redundant static-conformance
assertion that its source is one assignment containing only literal material.
Such a test is defense in depth and does not establish security. The structural
boundary is non-execution plus exact canonical-data decoding.

## 12. Python implementation/version disposition

The security property does not depend on CPython bytecode, frame layout,
attribute filtering, object internals, or version-specific sandbox behavior.
The repository's existing `requires-python = ">=3.12"` remains ordinary runtime
compatibility authority, not a security boundary introduced here.

The declarative bytes and canonical-data equality must be identical on every
supported repository Python version. Any implementation that compiles or
executes the validator resource rejects regardless of interpreter version.

## 13. Import and cache disposition

The validator resource performs no imports. No standard-library exposure table,
facade, wrapper, controlled validator builtins, guarded validator import,
validator module cache, namespace shell, source loader, or meta-path finder is
used for this component.

The already frozen `ControllerPureImportSession` machinery remains available
for other governed components only where separately authorized. It is not
entered for `rq003-experiment-005-configuration-validator-v1`.

Before any import-session or cache path, dispatch checks the component
identifier and requires the exact declarative policy. Attempting to route this
identifier through `AuthenticatedControllerPureSourceLoader`,
`ControllerPureClosureMetaPathFinder`, `controller_pure_guarded_import`,
`compile`, `exec`, or ordinary import is a hard failure.

Because no validator module is created, success and failure leave no validator,
helper, facade, wrapper, exception, namespace shell, or transitive validator
module in `sys.modules`. Existing controller cache state remains governed by
the detached controller's ordinary restoration and test authority.

## 14. Helper-source modification disposition

The exact disposition is:

**HELPER SOURCES REMAIN UNCHANGED AND OUTSIDE THE GOVERNED RUNTIME CLOSURE.**

No modification is authorized or required for:

- `src/orev3/execution/canonical.py`; or
- `src/orev3/features/rq003_contracts.py`.

The readiness controller may continue using `canonical.py` as trusted internal
implementation. `rq003_contracts.py` is used only by parity tests. A future
finding that either helper must reenter the governed runtime is a governance
stop, not implementation discretion.

## 15. Configuration-resource governance compatibility

The structural model is compatible with the frozen configuration-resource
governance. It preserves:

- adapter declaration v4 and its exact resource object;
- configuration/schema/validator byte and component authentication;
- `CONTROLLER_PURE` worker kind;
- detached Phase-3A invocation immediately after adapter, implementation
  binding, and profile reconstruction;
- exact validation request;
- `AuthenticatedExperimentConfigurationResource` success result;
- current-readiness rerun and comparison;
- no readiness-record field or evidence-kind revision;
- no implementation-binding schema revision;
- generation/overlay model;
- registry-first reconstruction;
- configuration/schema/validator Source-S scopes; and
- all resource/adapter/implementation/profile equalities.

The phrase “validator invocation” is refined to mean parsing the authenticated
declarative component and invoking the fixed trusted controller engine. It does
not mean importing or executing the component source. No frozen identity field,
schema coordinate, result field, readiness lifecycle state, or scientific
semantic changes.

## 16. Exact production path set

The frozen configuration-resource production path set remains exact. This
decision adds no production path and removes none:

Existing / modify:

- `src/orev3/execution/readiness_record.py`;
- `src/orev3/execution/registry.py`;
- `src/orev3/execution/phase3b_components.py`;
- `src/orev3/execution/readiness_contracts.py`;
- `src/orev3/execution/preparation.py`;
- `src/orev3/execution/evidence_preparation.py`;
- `src/orev3/execution/evidence_preparation_worker.py`;
- `src/orev3/execution/detached_evidence.py`;
- `src/orev3/execution/readiness_candidate.py`;
- `src/orev3/execution/current_readiness.py`; and
- `src/orev3/execution/git_state.py`.

New / create:

- `src/orev3/execution/schemas/v1/adapter-declaration-v4.schema.json`;
- `src/orev3/execution/schemas/v1/rq003-experiment-005-configuration.schema.json`;
  and
- `src/orev3/experiments/rq003_experiment5_configuration.py`.

`phase3b_components.py` owns the declarative parser and trusted validation
engine. The new validator path contains only Section 5 bytes. No helper-source,
new sandbox, worker, projection, Replay, outcome, provider, or generic runtime
path is authorized.

## 17. Exact test path set

The frozen nine-path test surface remains exact:

- `tests/execution/test_experiment_configuration_resource.py`;
- `tests/experiments/test_rq003_experiment5_configuration.py`;
- `tests/execution/test_phase3a_preparation.py`;
- `tests/execution/test_phase3b_authority.py`;
- `tests/execution/test_phase3b_integration.py`;
- `tests/execution/test_phase3c_readiness_contracts.py`;
- `tests/execution/test_phase3c_readiness_record_v2.py`;
- `tests/execution/test_phase3c_readiness_candidate.py`; and
- `tests/execution/test_phase3c_current_readiness.py`.

Ownership is exact:

- `test_phase3b_authority.py` proves declarative non-execution, one-member
  closure, parser/engine authority, and direct reflective escape containment;
- `test_phase3b_integration.py` proves the actual detached v4 path never imports
  or executes the validator and completes with no validator/helper cache delta;
- `test_rq003_experiment5_configuration.py` proves semantic and byte parity;
- `test_experiment_configuration_resource.py` proves resource/component/result
  identities and substitutions; and
- the remaining five tests retain their already frozen Phase-3A, contracts,
  readiness-record, candidate, and current-readiness responsibilities.

No new test path is required or authorized.

## 18. Mandatory positive parity matrix

Future tests must prove, over fixed vectors and generated bounded inert values:

- strict readiness JSON parsing and canonical encoding parity with
  `orev3.execution.canonical`;
- closed configuration-schema validation parity for every accepted and
  rejected schema/configuration fixture;
- exact RQ-003 canonical envelope byte parity with
  `orev3.features.rq003_contracts:canonical_encode` for every supported scalar,
  sequence, mapping, and complete configuration identity material;
- domain-identity parity;
- Experiment-specific configuration identity parity;
- Research Specification v2 profiled configuration identity parity;
- exact protocol/source-processing/profile/resource/adapter/implementation
  cross-check parity;
- exact accepted/rejected configuration case parity;
- deterministic repeated-run success and failure identities; and
- successful detached construction of the exact existing
  `AuthenticatedExperimentConfigurationResource`.

Any parity difference is a hard failure and requires prospective governance;
the implementation writer may not alter either frozen oracle.

## 19. Mandatory structural negative matrix

Tests must inject each representative escape attempt into substituted validator
bytes and prove rejection because the bytes are not the exact declarative form,
without executing the substitution:

- dataclass-generated method
  `__init__.__globals__["__builtins__"]["__import__"]`;
- ordinary Python wrapper `__globals__`;
- class/type/metaclass MRO, subclass, and class-dictionary traversal;
- Enum-generated class reflection;
- exception `__traceback__`, frame, globals, and builtins recovery;
- bound-method, descriptor, function/class reduction, closure, loader, and
  module recovery;
- callable-instance and ordinary module reflection;
- direct or recovered ambient `__import__`, `builtins`, `importlib`, `os`,
  `sys`, `pathlib.Path`, `subprocess`, or `socket`;
- filesystem open/stat/glob, network, process creation, environment access,
  provider/outcome code, and arbitrary project-module access;
- an import, function, lambda, class, decorator, call, comprehension,
  generator, exception statement, annotation, docstring, comment, second
  assignment, extra field, unknown operation, reordered operation, alternate
  prefix, noncanonical JSON, BOM, CRLF, missing LF, or trailing byte;
- routing the identifier through compile/exec/eval/runpy/importlib, the
  authenticated source loader, meta-path finder, guarded import, or ordinary
  import;
- reintroducing `canonical.py`, `rq003_contracts.py`, or another member into the
  governed component closure;
- forged/stale/cross-commit validator spec, component, schema, configuration,
  request, or authenticated result; and
- controller exception/traceback/message leakage into the closed failure
  response.

Structural proof requires that substituted executable bytes never run. An AST
rejection test alone is not acceptance evidence; tests must instrument import,
compile, exec, callbacks, filesystem, network, process, environment, provider,
and outcome sentinels and prove zero invocation at the actual controller and
detached boundaries.

## 20. Scientific and readiness disposition

The scientific disposition remains:

**SCIENTIFICALLY COMPATIBLE.**

No Experiment 005 population, source, measurement, feature, ranking, metric,
fold, bootstrap, inference, disposition, or confirmation rule changes.

The readiness disposition remains:

**NARROW ADAPTER/READINESS REVISION SUFFICIENT.**

No broader Execution Readiness revision, readiness-record schema field,
evidence kind, lifecycle state, implementation-binding schema revision,
provider boundary, or outcome boundary is required.

## 21. Dependency order

The exact sequence remains:

```text
configuration-resource readiness governance
  -> standard-library/capability-isolation governance freeze
  -> independent exact-byte/remote verification
  -> only then adapter-v4/readiness implementation authorization
```

This decision authorizes no successor step.

## 22. Explicit forbidden scope

This decision grants no authority for:

- declarative validator, parser, engine, or other implementation;
- adapter-v4/readiness implementation;
- helper-source modification;
- test modification;
- production adapter creation or adoption;
- registry modification;
- Source S, readiness evidence, candidate, E, R, or `EXECUTION_READY`;
- outcome-gate provenance implementation or outcome access/evaluation;
- provider/backend, allocation, namespace, or control authority;
- experiment/ranking/evaluation execution;
- confirmation-dataset selection;
- Strategy or Paper Miner work; or
- wallet, transaction, capital, or SOL access or use.

## 23. Remaining authority boundary

The structural model, declarative bytes, fixed operation sequence, non-executed
decoding, one-member closure, trusted engine location, helper disposition,
failure material, path sets, parity obligations, and structural negative tests
are prospectively closed by this decision. Future Git blob and SHA-256 values
remain implementation-byte-derived rather than implementation choices.

This decision is adopted and frozen prospectively. It authorizes no
implementation. No implementation may begin before this adoption is committed,
pushed, and independently verified.
