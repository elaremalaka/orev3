# RQ-003 Feature Set 1 Design

## Status

Research design only. This document inventories observable measurements. It
does not define feature implementations, derived features, models, rankings,
or strategies.

## Authority and scope

This design is governed by:

- [RQ-003](../questions/RQ-003-winning-square-predictability.md);
- the [Decision-Time Feature Audit](../questions/RQ-003-feature-audit.md);
- the [Feature Eligibility Resolution](../questions/RQ-003-feature-eligibility-resolution.md);
- the [Phase 3 Feature Design Review](rq003-phase3-design-review.md); and
- [Discovery Session 1](../notebook/discovery-session-001.md),
  [Session 2](../notebook/discovery-session-002.md),
  [Session 3](../notebook/discovery-session-003.md), and
  [Session 4](../notebook/discovery-session-004.md).

The inventory is grounded in the immutable observation and Strategy Lab
contracts in `src/orev3/data/models.py` and
`src/orev3/strategy_lab/interfaces.py`. The relevant boundary is the frozen
normal observation selected before the outcome is revealed. Later
observations, finalized state, RFC-012 evidence, and enriched outcomes are not
part of this inventory.

## Measurement criteria

A **fundamental measurement** is a value copied from the frozen normal
observation without arithmetic, comparison, classification, historical
reconstruction, or outcome attachment.

For this assessment:

- **Directly observable** means the value is present in the source observation,
  rather than constructed by the research feature framework.
- **Deterministic** means the same accepted observation yields the same value.
- **Atomic** means the value measures one observable concept. Each element of a
  25-square vector is one atomic measurement; the vector is an ordered family
  of those measurements.
- **Decision-time** means the value is available in the frozen normal
  observation before outcome revelation.
- **Independent** means the value is not semantically derivable from another
  retained measurement under the authoritative observation schema. It does
  not mean statistical independence.

A protocol may internally calculate a field before publishing it. Such a
field is still direct at the ORE Miner V3 observation boundary when the frozen
observation preserves the published value verbatim. Direct observability does
not, by itself, make a field eligible for prediction.

For cross-account protocol state, the frozen normal observation is the sole
decision-time authority. A measurement reads the Board, active Round, or
Treasury value preserved in that observation without issuing a supplementary
read, substituting a later value, or inferring that separately read accounts
share one RPC response context. The observation boundary preserves what was
observed; it does not authorize cross-account repair or reinterpretation.

## Measurement domains

The decision-time observation contains four measurement domains:

| Domain | Ownership | Observable subject |
| --- | --- | --- |
| Protocol state | ORE protocol accounts | Active-round and Board state published by the protocol |
| Temporal state | Protocol and observer envelope | Absolute ordering coordinates and relative round progress |
| Participant state | Active Round account | Per-square deployment and participation state plus round aggregates |
| Treasury state | Treasury account | Treasury value observed with the active round |

Identifiers and collection metadata locate or validate an observation but do
not measure the economic or competitive state of a round. They are therefore
treated separately from the four measurement domains.

## Candidate measurement assessment

### Protocol state

| Candidate measurement | Source | Direct | Deterministic | Atomic | Decision-time | Independent | Disposition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Board production-cost EMA | `board.production_cost_ema` | Yes | Yes | Yes | Yes, when present in the frozen observation | Yes | Fundamental protocol measurement read directly from the frozen observation. It is a protocol-maintained, lagged aggregate whose reset and revision semantics remain bound to its definition. |
| Active-Round motherlode | `round.motherlode` | Yes | Yes | Yes | Yes, only before finalization | Yes | Fundamental protocol measurement of the active Round's initialized pre-finalization payout field. It is not the live Treasury pool; a finalized nonzero payout remains outcome information. |
| Per-square reward value | `round.rewards[square]` | Yes | Yes | Yes, per square | Yes | Unresolved | Deferred. The approved eligibility review found that reward index semantics have not been proven sufficiently for feature use. |
| Mass | `round.mass[square]` | Yes | Yes | Yes, per square | Yes | Structurally separate, but empirically constant | Prohibited. The audited replay data contains constant zero mass, and repository policy excludes it as a predictive input. |
| Top-miner identity | `round.top_miner` | Yes | Yes | Yes | Present, but not an eligible measurement | Yes | Prohibited identity/outcome-sensitive field. It is not part of the fundamental predictive set. |
| Slot hash | `round.slot_hash_hex` | Yes | Yes | Yes | Present in raw observation only | Yes | Excluded from `DecisionContext`; not an eligible measurement. |
| Entropy | `round.entropy` | Yes, when present | Yes | Yes | Not safely decision-time for RQ-003 | Yes | Prohibited outcome-sensitive state. |

### Temporal state

| Candidate measurement | Source | Direct | Deterministic | Atomic | Decision-time | Independent | Disposition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Board start slot | `board.start_slot` | Yes | Yes | Yes | Yes | Yes | Structural chronology input only; rejected as a predictive feature. |
| Board end slot | `board.end_slot` | Yes | Yes | Yes | Yes | Yes | Structural chronology input only; rejected as a predictive feature. |
| Round expiry timestamp | `round.expires_at` | Yes | Yes | Yes | Yes | Yes | Structural lifecycle input only; rejected as a predictive feature. |
| RPC slot | `rpc_slot` | Yes | Yes | Yes | Yes | Yes | Observation-ordering and validation coordinate; explicitly prohibited as feature input. |
| Observation timestamp | `observed_at_utc` | Yes | Yes | Yes | Yes | Yes | Collection provenance and chronology; explicitly prohibited as feature input. |
| Slots elapsed | Replay-normalized context | No | Yes | Yes | Yes | No | Approved derived measurement class, not fundamental. |
| Slots remaining | Replay-normalized context | No | Yes | Yes | Yes | No | Approved derived measurement class, not fundamental. Missingness must remain explicit. |

The temporal domain therefore contributes no eligible **raw fundamental
predictive measurement** to Feature Set 1. Absolute timing values remain
necessary structural inputs. Approved relative timing measurements belong to
later derivation, not to this fundamental set.

### Participant state

| Candidate measurement | Source | Direct | Deterministic | Atomic | Decision-time | Independent | Disposition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Deployed lamports for one square | `round.deployed_lamports[square]` | Yes | Yes | Yes, per square | Yes | Yes | Fundamental participant measurement. The 25-element array is an ordered family of these atomic values. |
| Miner count for one square | `round.miner_counts[square]` | Yes | Yes | Yes, per square | Yes | Yes | Fundamental participant measurement. The 25-element array is an ordered family of these atomic values. |
| Total miners | `round.total_miners` | Yes | Yes | Yes | Yes | Yes | Fundamental participant aggregate. It is not assumed to equal the sum of per-square counts because a protocol participant may be represented on more than one square. |
| Pre-finalization total vaulted | `round.total_vaulted` | Yes | Yes | Yes | Yes only from the frozen normal observation | Yes | Fundamental revision-scoped aggregate approved by the eligibility resolution. Its semantic identity must bind the governing protocol revision. |
| Pre-finalization total winnings | `round.total_winnings` | Yes | Yes | Yes | Yes only from the frozen normal observation | Yes | Fundamental legacy-revision aggregate approved by the eligibility resolution. It must not be treated as semantically identical to a differently named or defined successor-protocol field. |

### Treasury state

| Candidate measurement | Source | Direct | Deterministic | Atomic | Decision-time | Independent | Disposition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Treasury motherlode | `treasury.motherlode` | Yes | Yes | Yes | Yes | Yes | Fundamental treasury measurement of the live pool available after the previous reset. It remains separate from the active Round's pre-finalization payout field. |

### Structural identity and provenance

The following values are directly observable but are not measurements in
Feature Set 1:

| Value class | Examples | Role | Feature disposition |
| --- | --- | --- | --- |
| Schema identity | `schema_version` | Decode and compatibility validation | Structural metadata only; prohibited as a predictive input. |
| Round identity | top-level, Board, and Round `round_id` values | Join, continuity, and consistency proof | Prohibited as a predictive input; aliases are not independent measurements. |
| Square identity | Ordered square index or identifier | Coordinate for per-square measurements | Structural key only; it must not become a ranking signal by itself. |
| Collector identity | `collector_session_id` | Collection provenance | Prohibited. |
| Source identity | Source path, line, or observation reference | Audit and reconstruction | Prohibited. |
| Protocol revision identity | RFC-014 provenance | Decode, validation, compatibility, and research stratification | Audit and eligibility information only; prohibited from `DecisionContext`, features, and Strategy. |
| Capture and outcome provenance | RFC-012 capture mode and outcome source | Outcome reconciliation and audit | Outcome-boundary information only; prohibited from feature input. |

Finalized state, winning square, winning miner, finalized motherlode,
finalized aggregates, and any other attached outcome fields are absent from
the fundamental set. They are labels or evaluation facts after the outcome
boundary, never measurements available to a decision-time feature.

## Minimal fundamental measurement set

The minimal eligible set is the union of the following direct measurement
families:

### Cross-revision-shaped core

1. Per-square deployed lamports.
2. Per-square miner counts.
3. Total miners.
4. Board production-cost EMA.
5. Active-Round motherlode.
6. Treasury motherlode.

“Cross-revision-shaped” means that corresponding fields may exist across
revisions. It does not assert semantic compatibility. Every eventual feature
definition still requires an exact, approved protocol-semantic binding.

### Revision-scoped direct aggregates

1. Pre-finalization total vaulted.
2. Pre-finalization total winnings for the protocol revision that defines that
   field and meaning.

These aggregates are fundamental at the observation boundary because the
framework reads them directly. They are revision-scoped because RFC-014 does
not permit a field rename or changed protocol meaning to inherit an existing
semantic identity silently.

The set excludes identifiers, absolute chronology, observer cadence, outcome
state, and unresolved reward semantics. It is minimal in the architectural
sense: removing any retained family would remove a directly observed concept
that cannot be reconstructed from the remaining retained families without an
additional assumption.

## Fundamental versus derived measurements

### Fundamental measurements

Fundamental measurements are the direct families listed in the minimal set.
They preserve protocol-published values exactly, along with the structural
square coordinate required for ordered per-square values. They require no
historical window and no interpretation.

### Derived measurement boundary

The following are derived categories and are not defined by this document:

- relative timing measurements;
- within-observation shares, proportions, normalization, and ranks;
- comparisons between protocol quantities;
- changes between observations;
- observation-count or cadence measurements;
- historical rolling-window summaries;
- leader persistence or ordering stability;
- labels, classes, scores, predictions, or recommendations.

This separation does not approve or reject a future derived feature. Any such
feature remains subject to its governing RQ-003 eligibility decision, the
Phase 3 design principles, and an independently identified deterministic
definition.

## Boundary conclusions

1. The irreducible decision-state quantities are protocol-published scalar or
   per-square values preserved in the frozen normal observation.
2. Temporal coordinates are essential to freeze and validate that observation,
   but absolute chronology is not an eligible predictive measurement.
3. Protocol revision, collection provenance, and RFC-012 outcome provenance
   remain audit and validation information; none enters a feature value.
4. Outcome fields never qualify as decision-time measurements, even when they
   are later attached to the same replay round.
5. A 25-square vector is not a compound interpretation: it is a canonically
   ordered family of 25 atomic measurements of one concept.
6. Feature Set 1 establishes measurement primitives only. It makes no claim
   about usefulness, predictive information, or strategy behavior.
