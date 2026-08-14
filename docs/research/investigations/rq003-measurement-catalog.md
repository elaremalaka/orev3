# RQ-003 Measurement Catalog

## Status

Research catalog only. This document does not approve a derived measurement,
feature, feature family, model input, ranking input, or Strategy input. Every
item described as “possible” remains unapproved until it independently
satisfies the governing RQ-003 eligibility and feature-definition process.

## Authority

This catalog is governed by:

- [RQ-003](../questions/RQ-003-winning-square-predictability.md);
- the [Decision-Time Feature Audit](../questions/RQ-003-feature-audit.md);
- the [Feature Eligibility Resolution](../questions/RQ-003-feature-eligibility-resolution.md);
- the [Phase 3 Feature Design Review](rq003-phase3-design-review.md);
- [RQ-003 Feature Set 1 Design](rq003-feature-set-1-design.md); and
- [RFC-014 Protocol Revision Provenance](../../../rfcs/RFC-014-PROTOCOL-REVISION-PROVENANCE.md).

The Feature Set 1 design approved eight fundamental measurement families:

1. per-square deployed lamports;
2. per-square miner counts;
3. total miners;
4. Board production-cost EMA;
5. Active-Round motherlode;
6. Treasury motherlode;
7. pre-finalization total vaulted; and
8. pre-finalization total winnings for the revision that defines that field.

Approval of a fundamental source measurement does not approve a transformation
of it.

## Catalog rules

### Candidate status

All possible derived measurements and feature families in this catalog have
the status **unapproved candidate**. A catalog entry records conceptual
adjacency only. It does not establish:

- usefulness;
- predictive information;
- a formula;
- arithmetic, tie, missingness, or history semantics;
- eligibility across one or more protocol revisions;
- a canonical feature identity; or
- permission to implement.

### Protocol dependency

A protocol dependency is a fact about account meaning, unit, cardinality,
lifecycle, or aggregation that must remain true for a measurement to retain
its meaning. Structural byte compatibility is insufficient.

### Revision dependency

RFC-014 Protocol Revision Identity and Semantic Compatibility Declarations
govern revision meaning. Protocol revision is provenance and population-control
information only. It must not enter a feature value, dependency, tie-breaker,
ranking input, or Strategy input.

A measurement with changed semantics receives a different feature semantic
identity or is excluded from cross-revision use. This catalog does not declare
any cross-revision semantic compatibility.

### Global prohibited derivations

The following are prohibited for every measurement in this catalog:

- any value using the winning square, winning miner, `won`, entropy, finalized
  outcome fields, or outcome provenance as input;
- any value using an observation after the frozen decision boundary;
- any value using RFC-012 post-transition evidence or enrichment as feature
  input;
- any value substituting a finalized field for its frozen pre-finalization
  value;
- any value using round, slot, timestamp, collector, source, capture-mode,
  protocol-revision, or activation identity as a predictive signal;
- any nondeterministic, mutable, environment-dependent, or hidden-state
  transformation;
- any transformation whose meaning depends on implicit feature order or on
  another registered feature's output;
- any classification, score, prediction, recommendation, or economic
  interpretation presented as a measurement; and
- any derivation from `mass`, whose audited replay value is constant zero and
  whose use is explicitly prohibited by repository policy.

## 1. Per-square deployed lamports

### Fundamental measurement

`round.deployed_lamports[square]` is the protocol-published lamport amount on
one of the 25 ordered squares in the frozen normal observation.

### Possible derived measurements

Unapproved candidates include:

- position of one square's deployment within the contemporaneous 25-square
  deployment distribution;
- one square's proportion of the contemporaneous board deployment;
- one square's difference or ratio relative to a contemporaneous board
  reference quantity;
- contemporaneous board-level totals, dispersion, concentration, or occupancy
  summaries constructed from the full vector;
- local-board or neighborhood summaries when the board topology is explicitly
  and immutably defined; and
- changes or summaries across eligible earlier observations when an approved
  history policy exists.

No formula, denominator, tie rule, topology, or history window is approved by
this list.

### Possible feature families

- raw current-state measurement;
- current-board relative measurement;
- current-board distribution measurement;
- board-topology measurement; and
- historical movement measurement.

The historical family remains subject to the existing cadence and lifecycle
coverage deferrals.

### Protocol dependencies

- a fixed, canonically ordered 25-square board;
- the Round field representing aggregate deployed lamports per square;
- lamports remaining the native unit of the observed values;
- exact Deploy aggregation and authority-round-square semantics; and
- the frozen value coming from the active Round before outcome attachment.

### Revision dependencies

Any change to square count, square ordering, deployment denomination,
aggregation, top-up rules, or authority semantics changes the measurement's
semantic scope. Cross-revision reuse requires an authoritative compatibility
declaration; similar field shape alone is not enough.

### Prohibited derivations

- winner-relative deployment or deployment on the winning square;
- final-board deployment substituted for the frozen vector;
- SOL return, expected reward, ROI, or capital-efficiency interpretation;
- a ranking that uses square identity as an unreported tie signal; and
- any transformation that silently treats lamports as SOL, a percentage, or a
  participant budget.

## 2. Per-square miner counts

### Fundamental measurement

`round.miner_counts[square]` is the protocol-published count of distinct Miner
authorities recorded on one square in the frozen normal observation.

### Possible derived measurements

Unapproved candidates include:

- position of one square's count within the contemporaneous 25-square count
  distribution;
- one square's proportion of a declared contemporaneous count total;
- differences or ratios relative to a contemporaneous board reference;
- board-level count totals, dispersion, concentration, or occupancy summaries;
- relationships between miner count and deployed lamports at the same frozen
  observation; and
- changes or summaries across eligible earlier observations under an approved
  history policy.

### Possible feature families

- raw current-state measurement;
- current-board relative measurement;
- current-board distribution measurement;
- cross-measurement participant-state relationship; and
- historical movement measurement.

### Protocol dependencies

- a fixed, ordered 25-square count vector;
- one count entry representing distinct Miner authorities recorded on that
  square;
- the protocol's authority-round-square insertion rules; and
- the distinction between a square count and the round-wide unique-authority
  count.

### Revision dependencies

A change to Miner identity, authority delegation, duplicate prevention,
per-square counting, board size, or account lifecycle changes the meaning.
Cross-revision pooling requires semantic compatibility for the count itself,
not merely the continued presence of 25 integers.

### Prohibited derivations

- treating a count as a number of natural persons, machines, transactions, or
  units of capital;
- winner-conditioned or finalized count measurements;
- assuming the sum of per-square counts equals `round.total_miners`;
- using collection cadence or observation count as participant activity; and
- silently replacing missing or malformed square counts.

## 3. Total miners

### Fundamental measurement

`round.total_miners` is the protocol-published number of unique Miner
authorities that have participated in the active round at the frozen normal
observation.

### Possible derived measurements

Unapproved candidates include:

- relationships between round-wide unique participation and per-square count
  totals;
- contemporaneous participation ratios using an explicitly declared
  denominator;
- relationships between total miners and contemporaneous deployed lamports;
- changes across eligible earlier observations; and
- normalization by an approved relative-round-position measurement.

### Possible feature families

- raw current-state measurement;
- current-round aggregate measurement;
- cross-measurement participant-state relationship; and
- historical participation measurement.

### Protocol dependencies

- `total_miners` retaining unique Miner-authority semantics;
- first-participation counting remaining distinct from per-square counting;
- a stable definition of Miner authority; and
- the value being captured before finalization.

### Revision dependencies

Changes to authority identity, automation/delegation semantics, round
participation rules, or when the counter increments require a new semantic
assessment. Revision identity may stratify research populations but may not be
used in the calculation.

### Prohibited derivations

- interpreting the value as natural people, wallets, machines, or transaction
  count;
- reconstructing it by summing per-square counts;
- using a finalized count or later observation; and
- labeling participation as high, low, crowded, or favorable inside the
  measurement layer.

## 4. Board production-cost EMA

### Fundamental measurement

`board.production_cost_ema` is the protocol-published production-cost
exponential moving average present in the frozen Board observation. It is a
protocol-maintained, lagged aggregate established by qualifying earlier reset
processing. The Measurement Library reads the published value directly and
unchanged; it does not reconstruct the aggregate. The value can carry forward
across a Board transition when that reset does not execute the qualifying
update path.

### Possible derived measurements

Unapproved candidates include:

- contemporaneous relationships with deployed lamports, total vaulted, or
  other approved economic-state measurements;
- normalization of a same-observation quantity by the EMA when units and
  zero-handling are explicitly compatible;
- changes across eligible earlier observations; and
- revision-homogeneous historical summaries under an approved history policy.

### Possible feature families

- raw protocol-state measurement;
- contemporaneous economic-state relationship;
- relative-scale measurement; and
- historical protocol-state measurement.

### Protocol dependencies

- exact field presence and nullability;
- the protocol-defined unit, update event, smoothing rule, and initialization
  behavior;
- qualifying-reset and carry-forward behavior; and
- the frozen Board observation being the authoritative value associated with
  the selected Round, without a supplementary read or later substitution.

### Revision dependencies

Any change to the EMA's input quantity, update schedule, arithmetic,
initialization, or economic meaning changes its semantics even if the account
field retains its name and width. No cross-revision equivalence is declared by
this catalog.

### Prohibited derivations

- reconstructing or imputing the EMA from later or finalized data;
- using field availability as a protocol-revision proxy;
- treating the EMA as participant cost, expected reward, return, or value;
- silently converting denomination; and
- replacing an absent value with an undeclared constant.

## 5. Active-Round motherlode

### Fundamental measurement

`round.motherlode` is the active Round's initialized pre-finalization
motherlode payout field in the frozen normal observation. Under the supported
protocol revision, it is initialized to zero and remains zero during the
active decision period. It is not the live Treasury pool. A nonzero value
assigned during finalization is outcome state and is ineligible for
decision-time consumption.

### Possible derived measurements

Unapproved candidates include:

- contemporaneous difference, ratio, or consistency relationships between
  Active-Round and Treasury motherlode values;
- normalization by another same-observation protocol quantity with compatible
  units; and
- changes across eligible earlier observations when an approved history policy
  exists.

### Possible feature families

- raw protocol-state measurement;
- cross-account consistency measurement;
- contemporaneous economic-state relationship; and
- historical protocol-state measurement.

### Protocol dependencies

- exact Active-Round motherlode semantics and denomination;
- lifecycle rules governing zero initialization and finalization-time payout
  assignment;
- the frozen normal observation being the sole authority for the active Round
  value, without cross-account repair or a later Round read;
- context consistency among the retained Board, Round, and Treasury values;
  and
- proof that the retained value precedes outcome revelation.

### Revision dependencies

Changes to motherlode contribution, hit, distribution, reset, or account
timing can change the field's meaning. A same-named value in another revision
is not automatically compatible.

### Prohibited derivations

- motherlode-hit labels, odds, or expected payout;
- finalized motherlode value or any value supplied by RFC-012 evidence;
- winner-conditioned motherlode allocation; and
- treating a difference between accounts as an error or signal without an
  approved semantic rule.

## 6. Treasury motherlode

### Fundamental measurement

`treasury.motherlode` is the live motherlode rewards pool published by the
Treasury account in the frozen normal observation. For an active Round, it is
the pool available after the previous reset; it is not the payout field on the
active Round. A later reset may transfer the then-current pool to the finalized
Round and establish a new Treasury value, but that later state cannot replace
the frozen decision-time value.

### Possible derived measurements

Unapproved candidates include:

- contemporaneous relationships with Active-Round motherlode;
- normalization against compatible same-observation protocol quantities; and
- changes across eligible earlier observations or earlier completed rounds
  under an approved history policy.

### Possible feature families

- raw treasury-state measurement;
- cross-account consistency measurement;
- contemporaneous economic-state relationship; and
- historical treasury-state measurement.

### Protocol dependencies

- exact Treasury field denomination and meaning;
- protocol contribution, distribution, and reset lifecycle;
- the frozen normal observation being the authoritative cross-account boundary
  without supplementary reads or later-value substitution;
- read-context consistency with the retained Board and Round state; and
- the value being captured at the decision boundary.

### Revision dependencies

Changes to Treasury layout, motherlode funding, emission, hit, distribution,
or reset semantics require renewed semantic assessment. Activation provenance
determines which meaning governs a round but cannot become feature input.

### Prohibited derivations

- future motherlode contributions or distributions;
- motherlode-hit probability, expected reward, or economic recommendation;
- later Treasury reads substituted into an earlier decision snapshot; and
- protocol-revision inference from field magnitude or availability.

## 7. Pre-finalization total vaulted

### Fundamental measurement

`round.total_vaulted` is the protocol-published aggregate present in the frozen
normal Round observation. Only the proven pre-finalization value belongs to
the approved fundamental measurement.

### Possible derived measurements

Unapproved candidates include:

- contemporaneous relationships with the 25-square deployed-lamport vector;
- relationships with total miners or production-cost EMA;
- differences or ratios against another same-unit, same-observation aggregate;
  and
- changes across eligible earlier observations under an approved history
  policy.

### Possible feature families

- raw pre-finalization aggregate;
- contemporaneous capital-state relationship;
- cross-account economic-state relationship; and
- historical aggregate movement.

### Protocol dependencies

- the exact definition and denomination of “vaulted” under the governing
  protocol;
- the event at which the aggregate changes;
- the distinction between deployed amounts and the vaulted aggregate; and
- proof that the value came from the frozen normal observation before
  finalization.

### Revision dependencies

Changes to deployment flow, vaulting, refund, settlement, or aggregation
semantics require a different semantic identity or exclusion. The field must
be interpreted within a revision-homogeneous segment unless authoritative
semantic compatibility says otherwise.

### Prohibited derivations

- finalized total vaulted or outcome-enriched replacement;
- returned principal, winnings, ROI, capture efficiency, or settlement
  interpretation;
- assuming equality with the sum of current deployments without an approved
  protocol proof; and
- pooling different revision meanings under one feature identity.

## 8. Pre-finalization total winnings

### Fundamental measurement

`round.total_winnings` is the legacy protocol aggregate present in the frozen
normal Round observation. Approval applies only to that pre-finalization value
and only to the protocol revision that defines its exact semantics.

### Possible derived measurements

Unapproved candidates include:

- contemporaneous relationships with total vaulted, deployed lamports, total
  miners, or production-cost EMA;
- same-unit differences or ratios whose operands have proven compatible
  semantics; and
- changes across eligible earlier observations under an approved history
  policy.

### Possible feature families

- raw revision-scoped pre-finalization aggregate;
- contemporaneous settlement-state relationship; and
- historical aggregate movement.

### Protocol dependencies

- the legacy definition and denomination of `total_winnings`;
- the lifecycle event at which the field changes;
- proof that the selected observation precedes finalization; and
- preservation of the exact serialized field meaning used by the governing
  decoder contract.

### Revision dependencies

This measurement is explicitly revision-bound. Official protocol history
changed the meaning of the serialized Round field from `total_winnings` to
`total_returned_sol` without changing its width or position. Those names and
meanings are not interchangeable. A successor field is a separate candidate
measurement requiring its own audit and semantic identity.

### Prohibited derivations

- reading the same serialized position as `total_winnings` under a revision
  that defines `total_returned_sol`;
- finalized winnings, returned SOL, or outcome-enriched values;
- expected return, ROI, economic valuation, or settlement recommendation;
- using a field name or decoder implementation as proof of semantic
  compatibility; and
- combining legacy and successor meanings under one derived-measurement or
  feature identity.

## Feature-family boundary summary

The catalog exposes the following possible family classes without approving
them:

| Possible family | Fundamental sources it may concern | Existing governing limitation |
| --- | --- | --- |
| Raw current state | Any one approved fundamental measurement | Still requires one reviewed semantic definition and executable binding |
| Current-board relative | Per-square deployed lamports or miner counts | Arithmetic, denominator, ties, units, and missingness must be declared |
| Current-board distribution | Full deployed-lamport or miner-count vector | Must remain measurement rather than interpretation or classification |
| Cross-measurement relationship | Two or more contemporaneous compatible measurements | Units and protocol semantics must be compatible; atomicity must be justified |
| Cross-account consistency | Board, Round, and Treasury measurements from one context | Must not reinterpret a difference without protocol authority |
| Board topology | Per-square vectors plus immutable topology | Topology and ordering must be explicit and revision-valid |
| Historical movement | One measurement across eligible earlier observations | Cadence, lifecycle coverage, history identity, and missingness remain unresolved where deferred |
| Revision-scoped aggregate | Total vaulted or legacy total winnings | Must remain within supported revision semantics unless compatibility is authoritative |

This table is a namespace of possible responsibilities, not a registry,
roadmap, eligibility decision, or implementation sequence.

## Catalog conclusions

1. The eight approved fundamental families provide direct decision-time
   measurement primitives; they do not imply approval of any transformation.
2. Per-square deployments and miner counts support the widest range of
   possible within-observation measurements, but no candidate formula or
   family is approved here.
3. Historical transformations remain constrained by cadence, lifecycle
   coverage, and immutable history semantics.
4. Protocol-maintained aggregates are direct at the observation boundary but
   retain their protocol-defined, revision-specific meanings.
5. `total_winnings` is a concrete example of why byte layout and field position
   cannot establish semantic compatibility.
6. Protocol revision remains provenance and population control, never a
   measurement or predictive input.
7. Outcome-boundary facts remain unavailable to every candidate derivation.
