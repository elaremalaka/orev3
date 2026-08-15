# RQ-003 Research Execution Specification v2

## Status

- Revision: `rq003-research-execution-specification-v2`
- State: Approved for implementation
- Compatibility: Additive to v1

This revision introduces exactly two immutable execution profiles while
preserving every v1 execution under its original binding. Historical artifacts
are neither migrated nor reinterpreted.

## 1. Execution profiles

An execution binds exactly one profile before Replay construction:

| Identity | Purpose |
| --- | --- |
| `outcome_aware_v1` | Outcome-blind ranking followed by authorized outcome joining and evaluation |
| `outcome_blind_characterization_v1` | Outcome-blind characterization that terminates without outcome capability |

The profile identity is immutable provenance. It participates explicitly in
the experiment binding, Replay identity, provenance identity, artifact graph,
and final manifest identity. A profile change therefore creates a different
execution.

## 2. Shared responsibilities

Both profiles share:

- specification, profile, experiment, configuration, source-commit, dataset,
  and protocol-revision bindings;
- deterministic Replay identity and canonical decision/candidate ordering;
- external-source validation and persisted-byte provenance;
- complete ordered pre-outcome population accounting;
- one frozen outcome-blind provenance block;
- predeclared artifact schemas and dependency identities;
- canonical generated artifacts and reconstructable artifact contracts;
- deterministic regeneration; and
- one sealed, profile-valid Experiment Audit Manifest.

Protocol revision and execution provenance remain validation metadata. They
must not enter measurements, Feature Sets, rankings, Strategy, or economics.

## 3. Shared lifecycle

```text
Experiment and profile binding
  -> source and Replay binding
  -> pre-outcome population accounting
  -> outcome-blind provenance freeze
  -> profile-specific primary artifact construction
  -> primary artifact validation
  -> profile-specific terminal lifecycle
```

The frozen provenance block contains the profile binding, Replay identity,
component identities, ordered population dispositions, completed upstream
contracts, and declared downstream artifacts. It contains no outcome, label,
outcome provenance, evaluation result, or outcome-derived exclusion.

## 4. Outcome-aware execution

The `outcome_aware_v1` profile produces and validates a ranking artifact before
outcome access is authorized. It then opens the declared outcome source, joins
outcomes, produces evaluation artifacts and ordered post-outcome dispositions,
and seals an outcome-aware terminal manifest.

Its manifest requires exactly one ranking primary artifact, at least one
outcome-source contract, at least one evaluation contract, complete
post-outcome dispositions for every eligible round, and the declared reports.
Evaluation artifacts must depend on both the frozen ranking and an immutable
outcome source.

Missing authorization, premature outcome access, source substitution,
fabricated labels, incomplete dispositions, or broken dependencies fail
closed.

## 5. Outcome-blind characterization

The `outcome_blind_characterization_v1` profile produces and validates a
characterization artifact, produces only declared outcome-blind descriptive
reports, and seals an outcome-blind terminal manifest.

Its runner receives no outcome source, outcome authorization, label provider,
evaluation callback, or equivalent capability. Its manifest requires exactly
one characterization primary artifact, complete terminal pre-outcome
population dispositions, all declared descriptive and conformance artifacts,
and the literal disposition
`outcome_access = prohibited_and_not_performed`.

Outcome-source contracts, authorizations, joins, evaluation artifacts,
evaluation dispositions, outcome provenance, outcome-dependent exclusions,
and outcome-aware dependencies are prohibited and fail closed.

## 6. Manifest union

The v2 Experiment Audit Manifest is a discriminated union containing common
execution material, the execution-profile binding, common artifact contracts,
common population accounting, and exactly one terminal extension:

- `OutcomeAwareTerminal`; or
- `OutcomeBlindCharacterizationTerminal`.

The profile determines the required extension, permitted artifact kinds,
population semantics, dependency graph, and terminal validation. An empty
outcome-aware extension is not an outcome-blind terminal.

## 7. Canonical artifacts and reconstruction

Framework-generated artifacts use canonical newline-terminated JSON or JSONL
bytes. Externally owned sources preserve their original bytes, digest, byte
count, record count, and ordering while receiving a separate canonical logical
content identity. Every declaration, dependency, content identity, persisted
digest, count, and owned identity reconstructs fail closed.

Regeneration with identical bindings and inputs must reproduce every generated
artifact and manifest byte-for-byte.

## 8. Compatibility

Research Execution Specification v1 remains immutable. Its bindings, schemas,
identity domains, validators, and artifacts remain authoritative for existing
Experiment 1 executions. V2 is additive and does not reinterpret v1.

Future outcome-aware executions bind v2 and `outcome_aware_v1`. Experiment 2A
is the first consumer of v2 and binds
`outcome_blind_characterization_v1`. Experiment 2B must bind
`outcome_aware_v1` before implementation or execution.

## 9. Acceptance criteria

Implementation is conformant when tests demonstrate:

- profile identity changes experiment, Replay, provenance, artifact, and
  manifest identities;
- the outcome-aware lifecycle preserves ranking freeze before outcome access;
- the characterization lifecycle completes without outcome capability;
- each profile rejects the other profile's terminal and artifacts;
- both profiles preserve complete population accounting;
- both manifests reconstruct and regenerate deterministically;
- generated artifacts remain canonically strict;
- existing v1 fixtures and executions remain reproducible; and
- neither profile leaks provenance or outcomes into decision-time inputs.
