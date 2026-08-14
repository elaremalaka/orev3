# RQ-003 Instrumentation Backlog

## Purpose

This document preserves the instrumentation improvements identified by
[Experiment 0B](../notebook/experiment-000-characterization.md). It is a
backlog, not an implementation authorization, architectural approval, or
change to the RQ-003 research protocol.

The items below remain subject to normal review and authorization. Their
absence does not invalidate the deterministic Experiment 0 artifact and does
not block Experiment 1. Protocol-revision provenance remains governed by
[RFC-014](../../../rfcs/RFC-014-PROTOCOL-REVISION-PROVENANCE.md), and the
decision-time information boundary remains governed by
[RQ-003](../questions/RQ-003-winning-square-predictability.md).

## Priority A — Nice to have before publication

### A1. Deterministic audit manifest

**Description:** Define a deterministic companion manifest that binds a
generated research artifact to its source dataset identity and hash, decision
configuration identity, governing protocol revision, ordered output schema,
record count, artifact byte length, and artifact digest. The manifest must
remain audit metadata and must not become measurement, feature, or Strategy
input.

**Motivation:** Experiment 0B reconstructed this information from the archive,
the generation invocation, and implementation constants. The reduced
Experiment 0 artifact does not preserve the complete generation context by
itself.

**Expected value:** A manifest would make publication artifacts easier to
authenticate, compare, reproduce, and review without relying on an external
narrative of the generation run.

**Why it is NOT currently blocking research:** Experiment 0 regenerated
byte-for-byte with identical identities, values, ordering, length, and
SHA-256. The required generation context is available from the governed source
dataset, configuration, and implementation even though it is not yet packaged
as one companion artifact.

### A2. Decision-identity provenance index

**Description:** Define a read-only audit index mapping each deterministic
decision identity to its replay round, selected source-observation identity,
lifecycle coverage classification, and decision-boundary selection distance.
The index must remain provenance and validation information; it must never
enter `DecisionContext`, a MeasurementVector, a feature, ranking, or Strategy
input.

**Motivation:** The intentionally narrow Experiment 0 record contains a
decision identity but no round or source-observation fields. Tracing an
individual vector to raw replay evidence currently requires deterministic
identity reconstruction against the replay source.

**Expected value:** The index would make anomaly review, source verification,
cadence auditing, and publication review faster while preserving the existing
future-information boundary.

**Why it is NOT currently blocking research:** Every decision remains
deterministically traceable by replaying the approved identity construction.
Experiment 0B found no ambiguous or duplicate decision groups, so the proposed
index improves convenience and auditability rather than correctness.

## Priority B — Instrumentation improvements

### B1. Artifact-only MeasurementVector identity verification

**Description:** Investigate instrumentation that would allow an independent
consumer to verify a `measurement_vector_identity` using an archived research
artifact and explicitly bound audit material, without rerunning the entire
measurement pipeline. This item does not authorize changing the Experiment 0
schema or exposing decision-prohibited information.

**Motivation:** Experiment 0 validates every full MeasurementVector through
canonical encoding and reconstruction before persistence. Its reduced output
retains only the vector identity and ordered values, not all canonical identity
material required for post-hoc reconstruction.

**Expected value:** Artifact-only verification would provide an additional
independent integrity check and simplify external review of archived research
outputs.

**Why it is NOT currently blocking research:** Generation-time reconstruction
already fails closed, and two complete Experiment 0 generations produced
identical 466,275-record artifacts and identical SHA-256 digests. The missing
capability is an extra post-hoc verification path, not a gap in current
deterministic generation.

### B2. Explicit generation-time versus artifact-time identity documentation

**Description:** Document which identity guarantees are established while the
pipeline holds the complete immutable execution context and which checks can
be repeated using only the reduced persisted artifact. The documentation
should distinguish full-vector canonical reconstruction from persisted-row
schema, ordering, syntax, uniqueness, and digest validation.

**Motivation:** Both validation layers are deterministic, but they operate on
different identity material. Without an explicit distinction, readers may
incorrectly assume that the reduced artifact alone contains every input needed
to reconstruct a full MeasurementVector identity.

**Expected value:** Clearer documentation would prevent overstatement of
artifact-only guarantees and make conformance reviews more precise.

**Why it is NOT currently blocking research:** The implementation behavior is
already unambiguous and was directly exercised by Experiment 0B. This item
improves communication of existing guarantees; it does not repair a failing
identity or execution invariant.

## Priority C — Monitoring

### C1. Trace the deployed-lamport outlier

**Description:** Trace the observed square-22 value of 4,264,350,439 lamports
through its decision identity to the replay observation and raw protocol
snapshot. Preserve the value unless source evidence demonstrates a data
integrity problem.

**Motivation:** It is the only deployed-lamport value above 2,000,000,000 and
is materially separated from the next-largest observed value of
1,614,874,593. It remains a valid unsigned integer and was not classified as
impossible by Experiment 0B.

**Expected value:** A provenance trace would distinguish a legitimate protocol
observation from a collection, decoding, replay, or transcription anomaly
without interpreting its research usefulness.

**Why it is NOT currently blocking research:** The value passes current type,
range, canonicalization, and identity validation. It is one traceable
observation, not evidence that the measurement family or generated dataset is
structurally invalid.

### C2. Continue monitoring revision-scoped constant measurements

**Description:** Continue recording the cardinality and range of
`active_round_motherlode`, `pre_finalization_total_vaulted`, and
`pre_finalization_total_winnings` for each governed protocol revision. Treat
the observed values exactly as published, without substitution,
normalization, or cross-revision pooling.

**Motivation:** All three measurements were constant zero in Experiment 0B.
That observation is consistent with the documented pre-finalization semantics
of the retained revision, but RFC-014 requires revision-scoped meanings to
remain explicit.

**Expected value:** Continued monitoring would detect schema, lifecycle, or
revision changes that alter the observed cardinality while preserving a clear
record of expected constants.

**Why it is NOT currently blocking research:** Constant values are neither
missing nor malformed, and no outcome-derived replacement occurred. Their
current behavior is a documented dataset property rather than an execution or
protocol inconsistency.

### C3. Continue monitoring replay decision-distance distribution

**Description:** Record the slot distance between each requested decision
boundary and its deterministically selected replay observation, together with
lifecycle coverage and exclusion counts, for future generated datasets.

**Motivation:** Experiment 0B found 18,590 decisions selected within two slots
of the target, 61 selected at least three slots earlier, a maximum distance of
145 slots, and two `partial_start` rounds with no eligible pre-boundary
observation.

**Expected value:** Monitoring would expose changes in observer cadence and
replay coverage, support RQ-003 validation controls, and make dataset
populations comparable without using cadence as a predictive input.

**Why it is NOT currently blocking research:** Every included decision obeyed
the approved deterministic selection rule and decision-time boundary. The two
ineligible rounds were excluded rather than fabricated, and the observed
distance distribution can be controlled explicitly in later research.

The current backlog items improve auditability and observability but do not prevent Experiment 1 from beginning.
