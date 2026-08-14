# RQ-003 Research Execution Specification

## Status

- Type: Repository-wide RQ-003 execution specification
- Revision: `rq003-research-execution-specification-v1`
- Domain: Research
- Implementation authorized: Documentation only

This specification owns the reusable execution mechanics common to RQ-003
experiments. Each experiment remains the sole owner of its scientific question,
hypotheses, measurements, Feature Set, baselines, ranking procedures, controls,
metrics, uncertainty method, interpretation rules, and result criteria.

## Authority

This specification is governed by:

- [RFC-010 — Deterministic Strategy Laboratory](../../rfcs/RFC-010-STRATEGY-LAB.md);
- [RFC-014 — Protocol Revision Provenance](../../../rfcs/RFC-014-PROTOCOL-REVISION-PROVENANCE.md);
- [RQ-003 — Decision-Time Winning-Square Information](../questions/RQ-003-winning-square-predictability.md);
  and
- the experiment protocol that binds this specification for a particular
  execution.

If an experiment conflicts with RFC-010, RFC-014, or RQ-003, the experiment is
ineligible. If an experiment-specific scientific requirement is stricter than
this specification without contradicting it, the stricter requirement governs
that experiment.

## 1. Scope

This specification defines only:

- versioning and immutable experiment binding;
- canonical identity construction;
- Replay identity construction;
- the Experiment Audit Manifest lifecycle;
- artifact integrity and reconstruction contracts;
- complete population-disposition accounting;
- the outcome-blind ranking freeze and subsequent outcome join; and
- execution conformance and fail-closed behavior.

It does not authorize an experiment, implementation, execution, or scientific
interpretation.

## 2. Explicit non-goals

This specification does not define or select:

- measurements or derived measurements;
- Feature Sets;
- research questions or hypotheses;
- baselines;
- ranking procedures or tie rules;
- metrics;
- bootstrap or other uncertainty parameters;
- scientific controls;
- scientific interpretation;
- success, failure, or inconclusive criteria;
- dataset eligibility rules or decision timing; or
- Strategy, Deployment, Evaluation, or RFC-011 Economics behavior.

Those responsibilities remain in the governing experiment protocol or their
existing architectural owner.

## 3. Versioning and experiment binding

### 3.1 Immutable specification revision

An execution shall bind exactly one immutable revision of this specification.
The binding uses the revision identifier and the SHA-256 digest of the exact
specification document. A later revision does not alter, supersede, or repair
an execution bound to an earlier revision.

### 3.2 Governing experiment binding

An execution shall bind exactly one immutable governing experiment protocol.
The binding records:

- the experiment protocol identifier and revision;
- the SHA-256 digest of the exact protocol document;
- the bound execution-specification revision and document digest; and
- the experiment-specific configuration identity.

The experiment-specific configuration is the ordered, canonical declaration
of values selected by the experiment, including its source population,
decision-selection configuration, component identities, artifact declarations,
and any other execution input required by that protocol. This specification
defines how those declarations are bound; it does not choose their values.

Changing either governing document, any experiment-specific declaration, or
their order creates a different binding and requires a distinct execution.

### 3.3 Source commit provenance

Every execution shall record the full Git commit SHA whose tree contains the
governing protocol, bound specification revision, and executing implementation.
All tracked protocol and implementation files used by the execution shall
match that commit. A value recorded only in a log, command transcript, path, or
later analysis is not authoritative source provenance.

Generated or ignored research artifacts do not change source commit provenance.
Uncommitted differences in a tracked governing document or executing source
invalidate the binding.

## 4. Canonical identity framework

### 4.1 Canonical encoding

All identities defined by this specification use the RQ-003 canonical encoding:

- UTF-8 JSON;
- sorted mapping keys;
- declared array order preserved;
- no insignificant whitespace;
- explicit `null` for schema-declared nullable fields;
- decimal integers without alternate representations;
- finite values only; and
- domain-separated SHA-256.

An identity-bearing object shall declare its schema and canonical-encoding
version. Unknown fields, missing required fields, duplicate logical fields,
non-finite values, unsupported scalar representations, and undeclared ordering
fail closed.

### 4.2 Identity form

Every identity has the form:

```text
identity = SHA256(domain || canonical(identity_material))
```

The domain is a fixed, versioned string unique to the identity kind. Identity
material contains every immutable semantic or structural field owned by that
identity and excludes the stored identity itself. Human-readable labels,
filesystem paths, runtime duration, process identity, and timestamps that do
not carry declared semantics are not identity authority.

### 4.3 Reconstruction and continuity

Before an artifact may be consumed, its identity shall be reconstructed from
its canonical material and compared with its stored identity. Every referenced
upstream identity shall already have reconstructed successfully. An artifact
may reference, but may not redefine, the identity of an upstream object.

Identity continuity is valid only when the exact reconstructed upstream
identity appears in the downstream artifact's canonical identity material.
Copying a human-readable name or digest into non-authoritative metadata does
not establish continuity.

## 5. Replay identity framework

### 5.1 Meaning

Replay identity is the deterministic identity of the exact outcome-blind,
ordered decision population presented to one experiment. It is provenance and
validation information only. It shall not become a `DecisionContext` value,
measurement value, Feature Set value, or ranking signal.

### 5.2 Required identity material

Every experiment shall bind the following ordered Replay identity material:

1. execution-specification revision identity;
2. governing experiment protocol identity;
3. experiment-specific configuration identity;
4. source commit provenance;
5. source replay dataset identity, version, schema identity, byte count, and
   SHA-256 digest;
6. the governing RFC-014 protocol-revision identity or homogeneous revision
   population identity required by the experiment;
7. the exact decision-selection configuration identity;
8. the canonical ordered replay-round identities; and
9. the experiment-declared canonical candidate order.

The experiment defines the decision-selection rule, population, chronological
ordering semantics, and candidate universe. This specification requires those
choices to be explicit and identity-bound.

### 5.3 Construction and recording

Replay identity is:

```text
SHA256(
  "rq003-research-replay-identity-v1" ||
  canonical(required_replay_identity_material)
)
```

The complete identity material and reconstructed Replay identity shall appear
in the outcome-blind provenance block and final Experiment Audit Manifest. A
dataset digest, list of round identifiers, runtime object identity, or Replay
identity from another experiment does not satisfy this contract.

## 6. Experiment Audit Manifest lifecycle

### 6.1 Authority

Each execution produces exactly one final Experiment Audit Manifest. Once
sealed, it is the authoritative record of execution provenance and artifact
relationships. A filename or serialization container is not prescribed; its
schema, canonical-encoding version, identity, byte count, and digest are.

### 6.2 Outcome-blind provenance block

Before any outcome is joined, the execution shall create one canonical
outcome-blind provenance block containing:

- specification and experiment bindings;
- source commit provenance;
- complete Replay identity material and identity;
- experiment-specific configuration identity;
- all declared pre-outcome component identities;
- the complete pre-outcome population accounting;
- every completed upstream pre-ranking artifact contract and reconstructed
  identity; and
- the declared identities and schemas of downstream artifact kinds.

The block shall contain no outcome, label, outcome provenance, evaluation
result, or outcome-derived exclusion.

### 6.3 Freeze and ranking-artifact binding

The outcome-blind provenance block shall be canonically encoded, identified,
and frozen before the outcome join. The ranking artifact shall include that
exact block identity in its own canonical identity material. The block cannot
contain the ranking-artifact identity, because that would create a circular
identity dependency.

After the block is frozen, neither its contents nor its identity may change.
Any correction requires a new execution binding and new artifacts.

### 6.4 Outcome-dependent extension

After the ranking artifact is frozen and validated, outcomes may be joined as
specified in Section 9. Outcome-dependent artifacts shall reference the exact
ranking-artifact identity and outcome-source identity. They shall not modify or
replace the ranking artifact or outcome-blind provenance block.

### 6.5 Final sealing

After execution completes, the final manifest shall contain:

- the complete frozen outcome-blind provenance block and its identity;
- the frozen ranking-artifact contract and identity;
- every outcome-source and outcome-join artifact contract and identity;
- every evaluation and reporting artifact contract and identity;
- complete pre-outcome and post-outcome population accounting;
- the execution conformance result; and
- the final manifest identity.

The manifest identity excludes only its stored identity field. The complete
manifest shall reconstruct successfully before it is sealed. Once sealed, it
is immutable. A partial or mutable manifest is not authoritative.

The manifest cannot contain its own persisted-byte digest or byte count as
identity material without creating a circular dependency. Those two sealing
facts are deterministic outputs reported with the sealed manifest, not inputs
to its content identity. This is the sole self-reference exception; all other
artifact contracts remain inside the manifest and fully identity-bound.

## 7. Artifact contracts

### 7.1 Required fields

Every authoritative artifact contract records:

- artifact kind and schema version;
- canonical-encoding version;
- ordered upstream dependency identities;
- canonical content identity;
- SHA-256 digest of the exact persisted bytes;
- exact byte count;
- exact logical record count;
- authoritative record ordering; and
- reconstruction status.

The canonical content identity and persisted-byte digest are distinct. The
first identifies canonical logical content; the second proves the exact stored
representation. Both are required.

### 7.2 Ordering

An artifact's governing experiment protocol declares its semantic record
order. Producers shall preserve that order. Consumers shall not sort, regroup,
deduplicate, or otherwise normalize an artifact implicitly. A different order
produces different canonical content and a different identity.

### 7.3 Deterministic reconstruction

An artifact is conformant only when a clean execution from the same bound
inputs reproduces:

- identical canonical logical content;
- identical canonical content identity;
- identical persisted bytes and SHA-256 digest;
- identical byte and record counts;
- identical ordering; and
- identical upstream identity references.

Operational metadata such as elapsed time may be recorded separately but
shall not participate in scientific or artifact identities unless an
experiment explicitly gives it semantics.

## 8. Population accounting

### 8.1 Pre-outcome dispositions

Every Replay-bound round shall receive exactly one pre-outcome terminal
disposition:

- `eligible`: the round produced the experiment-declared outcome-blind
  artifact; or
- `excluded`: the round did not, with one canonical categorical reason
  declared by the experiment.

Eligible and excluded sets shall be disjoint, contain no duplicates, preserve
canonical Replay order, and together account for every Replay-bound round.
Aggregate counts shall reconstruct from the ordered dispositions.

### 8.2 Eligible-round authority

The frozen ranking artifact is the authoritative ordered eligible-round
manifest when the governing experiment produces one ranking record per
eligible round. It shall record the immutable round and decision identities
required by that experiment. No redundant eligible-round artifact is required.

Replay identity does not satisfy disposition accounting because an identity
digest does not enumerate terminal dispositions.

### 8.3 Excluded-round authority

The outcome-blind provenance block is the authoritative location for ordered
pre-outcome exclusions and their reasons. It shall not include outcome-derived
reasons.

After outcome join, every eligible round shall also receive exactly one
experiment-declared evaluation disposition. Post-outcome dispositions and
counts belong in outcome-dependent artifacts and the final manifest; they
cannot rewrite pre-outcome eligibility.

## 9. Outcome-boundary mechanics

### 9.1 Ranking-artifact freeze

The complete outcome-blind ranking artifact shall be canonically encoded,
identified, durably persisted, and validated before any outcome source is
opened or joined. It shall reference the frozen outcome-blind provenance-block
identity and contain no outcome, label, outcome provenance, evaluation result,
or post-decision evidence.

The execution shall fail closed if the artifact cannot be frozen or if its
identity, byte digest, counts, ordering, dependencies, or schema do not
reconstruct.

### 9.2 Outcome join

Only after the ranking freeze succeeds may the execution open the immutable
outcome source authorized by the experiment. The join shall:

- consume the ranking artifact without mutation;
- bind the exact ranking-artifact and outcome-source identities;
- preserve pre-outcome eligibility and ordering;
- attach labels only through the experiment-declared join key;
- preserve outcome provenance; and
- record every post-outcome evaluation disposition without fabrication or
  imputation.

The join produces a new immutable artifact. It never updates the ranking
artifact in place.

### 9.3 Identity continuity

Every downstream evaluation or reporting artifact shall bind the exact outcome
join identity and its ordered upstream chain. No outcome-dependent artifact
may be substituted into an outcome-blind dependency position.

## 10. Execution conformance failures

An execution is nonconformant and no scientific result may be interpreted when
any of the following occurs:

- a required specification, experiment, source, Replay, component, or artifact
  identity is absent, ambiguous, unsupported, or fails reconstruction;
- canonical encoding is malformed, non-canonical, incomplete, or uses an
  undeclared version;
- an artifact's canonical identity, byte digest, byte count, record count,
  ordering, schema, or dependency identity differs from its contract;
- a required artifact is missing, duplicated, truncated, malformed, or cannot
  be parsed fail-closed;
- the outcome-blind provenance block changes after freeze;
- the ranking artifact changes after freeze or outcomes are accessed before
  its freeze succeeds;
- the final Experiment Audit Manifest changes after sealing;
- population dispositions are missing, duplicated, overlapping, unordered, or
  fail to account for the Replay-bound population exactly;
- source commit provenance is missing or does not match the tracked governing
  documents and executing source;
- outcome provenance is missing or identity continuity breaks across the
  outcome join;
- deterministic regeneration changes authoritative content, identity,
  persisted bytes, counts, ordering, or dependencies; or
- a consumer redefines an identity owned by an upstream component.

Execution nonconformance is distinct from a scientifically valid positive,
negative, or inconclusive result. The governing experiment defines scientific
invalidity and interpretation. A nonconformant execution cannot be repaired by
later analysis or by supplying missing provenance retroactively; it requires a
new execution under an authorized binding.

## 11. Conformance validation

Before scientific interpretation, validation shall establish objectively that:

1. the specification and experiment bindings reconstruct;
2. source commit provenance matches the executing tree;
3. Replay identity and every item of its material reconstruct;
4. all Replay-bound rounds have exactly one pre-outcome disposition;
5. the outcome-blind provenance block was frozen before the outcome join;
6. the ranking artifact binds that frozen block and contains no outcome data;
7. every artifact contract, dependency, digest, count, and order reconstructs;
8. the outcome join preserves ranking identity and ordering;
9. all post-outcome dispositions reconcile with the eligible population;
10. the final manifest reconstructs and is sealed; and
11. deterministic regeneration is byte-identical and identity-identical.

Conformance validation reports execution correctness only. It does not assess
scientific hypotheses, controls, metrics, or interpretation.

## 12. Architectural invariants

This specification preserves:

- RFC-010 decision-time purity and immutable `DecisionContext`;
- RFC-014 protocol revision as provenance and validation information only;
- the RQ-003 outcome boundary;
- separation between outcome-blind ranking and outcome-based evaluation;
- deterministic, immutable, reproducible research artifacts;
- fail-closed identity and provenance validation; and
- experiment ownership of every scientific decision.

No identity, manifest field, protocol revision, disposition, or operational
value defined here may become a measurement, Feature Set value, ranking input,
or Strategy input unless a separate governing architecture explicitly permits
that use.
