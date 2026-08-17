# RQ-003 Phase 2 — Feature Eligibility Resolution

## Status

**Type:** Research protocol deliverable

**Phase:** RQ-003 Phase 2

**Scope:** Resolution of conditional feature classes

**Implementation authorized:** No

This document resolves the conditional feature classes identified by
[RQ-003 Phase 1 — Decision-Time Feature Audit](RQ-003-feature-audit.md). It
does not engineer features, implement features, compare usefulness, rank
features, build a model, or authorize outcome evaluation.

## Authority

This resolution is governed by:

- [RQ-003 — Decision-Time Winning-Square Information](RQ-003-winning-square-predictability.md);
- [RQ-003 Phase 1 — Decision-Time Feature Audit](RQ-003-feature-audit.md);
- [Discovery Session 1 — Dataset Inventory](../notebook/discovery-session-001.md);
- [Discovery Session 2 — Round Evolution](../notebook/discovery-session-002.md);
- [Discovery Session 3 — Round Taxonomy](../notebook/discovery-session-003.md); and
- [Discovery Session 4 — Behavioral Dimensions](../notebook/discovery-session-004.md).

## 1. Decision standard

Conditional features are resolved by their shared eligibility question rather
than by their individual column names.

- **Approved:** current authority supplies enough evidence that the class can
  enter a later predeclared RQ-003 candidate schema without violating the
  decision boundary. Approval does not imply usefulness.
- **Rejected:** the class conflicts with an RQ-003 prohibition or the available
  evidence establishes that it represents a disallowed measurement or identity
  signal. Rejection applies to the class in its currently audited form.
- **Deferred:** the class is not architecturally prohibited, but a specific
  semantic or measurement proof is absent. Deferred means ineligible until a
  separate reviewed artifact supplies that proof.

Determinism alone is insufficient. A deterministic value may still encode
chronology, collection cadence, lifecycle coverage, or outcome information.

## 2. Resolution summary

| Feature class | Shared eligibility question | Decision |
|---|---|---|
| Absolute protocol timing fields | Can absolute slots be separated from chronology identity? | **Rejected** |
| Relative protocol timing fields | Are elapsed/remaining values contemporaneous protocol position rather than absolute identity? | **Approved** |
| Pre-finalization Round aggregates | Are values frozen before outcome revelation? | **Approved** |
| Reward-derived features | Do reward-array indices have validated square semantics, and are values demonstrably pre-finalization? | **Deferred** |
| Cadence-sensitive temporal differences | Do adjacent-observation dynamics remain meaningful across collection cadence? | **Deferred** |
| Observation-count and availability features | Do the values describe protocol behavior rather than observer coverage? | **Rejected** |
| Historical rolling-window features | Are observation-index windows comparable across cadence regimes? | **Deferred** |
| Leader persistence features | Can sampled leadership history be separated from cadence and lifecycle entry? | **Deferred**, except exact observation-count availability signals are **Rejected** |
| Earlier-round deterministic state | Is there a concrete, immutable, leakage-audited state definition? | **Deferred** |

## 3. Absolute protocol timing fields

### Class membership

- `start_slot`;
- `end_slot`;
- `board.start_slot`;
- `board.end_slot`; and
- `round.expires_at`.

Absolute `rpc_slot` was already prohibited in Phase 1 and remains prohibited.
The Board aliases do not create a separate class: they repeat the same absolute
slot identities.

### Governing concern

RQ-003 prohibits absolute chronology and accidental identity proxies as
predictive inputs. These values increase with chain history and can identify or
narrow the current round's chronological location even though they are valid
protocol fields at decision time.

### Architectural concern

The fields are present in `DecisionContext`, but presence is not feature
authorization. Their legitimate architectural purposes are replay selection,
round-boundary validation, and derivation of relative timing. Treating them as
candidate inputs would expose absolute chronology to the ranking procedure.

### Research concern

A procedure could associate temporal collection regimes, protocol revisions,
or a particular development interval with outcomes through absolute slot
values. Chronological held-out evaluation does not neutralize that identity
channel; it only changes where the channel appears.

### Evidence required

No further evidence can make the raw absolute values cease to encode
chronology. A different relative quantity would be a different feature class
and would require its own audit.

### Decision

**Rejected.**

### Justification

The raw fields are deterministic and contemporaneous but conflict with the
explicit RQ-003 ban on chronology proxies. They may remain structural inputs to
Replay and to the already audited relative `slots_elapsed` and
`slots_remaining` calculations. They may not enter a predictive candidate
schema.

## 4. Relative protocol timing fields

### Class membership

- `slots_elapsed`; and
- `slots_remaining` when available.

These were already marked eligible in Phase 1. They are included here to close
the timing question after rejecting their absolute source fields.

### Governing concern

The distinction is between position within the current protocol round and
absolute position in repository chronology.

### Architectural concern

Both values are constructed at the immutable decision boundary from the
selected normal observation. Neither requires a later observation or the final
outcome.

### Research concern

Availability during initialization must be preserved rather than guessed. The
value must not be reconstructed using the completed lifecycle's final
observation count.

### Evidence required

The existing Replay derivation and RQ-003 freeze rule supply the required
evidence. Later analysis must preserve missing `slots_remaining` as missing.

### Decision

**Approved.**

### Justification

The class expresses contemporaneous relative protocol position without
exposing the raw absolute slot identity. Approval does not authorize an
availability flag or imputation.

## 5. Pre-finalization Round aggregates

### Class membership

- `round.total_vaulted`; and
- `round.total_winnings`.

Other contemporaneous Round aggregates already marked **Yes** in Phase 1 are
unchanged.

### Governing concern

These account fields exist before and after finalization. Their eligibility is
temporal: the frozen pre-decision value is potential decision-time state, while
the finalized value is prohibited outcome information.

### Architectural concern

RQ-003 defines the decision context as the latest eligible normal observation
at or before the predeclared decision point. It separately prohibits finalized
values and freezes the ranking before outcome revelation. RFC-012 outcome
evidence cannot enter that snapshot side.

### Research concern

An evaluation must not select a context whose values already reflect
finalization, nor replace a frozen value with the finalized lifecycle outcome.
Physical field presence is not sufficient; provenance must remain the selected
normal observation.

### Evidence required

For each evaluated context, the existing RQ-003 replay/future-information audit
must prove that:

- the value comes from the selected normal observation;
- the observation precedes the outcome boundary;
- no finalized or enriched payload supplied the value; and
- the same selection rule applies to candidate procedures and baselines.

This is a required conformance check already imposed by RQ-003, not an
unresolved research study.

### Decision

**Approved.**

### Justification

The pre-finalization values are contemporaneous Round state explicitly exposed
by the immutable `DecisionContext`. Their finalized counterparts remain
prohibited. Approval applies only to the frozen pre-finalization values.

## 6. Reward-derived features

### Class membership

This class includes the raw reward vector and every existing current or
historical output that assigns a reward-array index to a candidate square:

- `round.rewards[0..24]`;
- `reward_raw`;
- `reward_delta_1`, `reward_delta_2`, and `reward_delta_3`;
- `reward_rolling_mean_2` and `reward_rolling_mean_3`;
- `reward_ema_0_5`;
- `reward_momentum_3`, `reward_momentum_1`, and
  `reward_acceleration_1`;
- `reward_rolling_std_3`;
- `reward_observations_since_became_leader`;
- `reward_consecutive_leader_observations`; and
- `has_reward_ever_led`.

Finalized reward values remain prohibited and are not conditional candidates.

### Governing concern

RQ-003 permits only inputs with known semantics at the decision boundary. The
repository records the 25-element array as raw protocol reward state and
explicitly does not assume that its indices map to the 25 board squares.

### Architectural concern

The array is contemporaneously visible, but the existing per-candidate feature
pipeline indexes it by `square_index`. Without a protocol-semantic proof, that
operation may assign unrelated array positions to candidates. Temporal reward
features inherit the same unresolved mapping and also inherit cadence concerns.

### Research concern

Using an unproven positional mapping would make the input's meaning undefined.
Observed numerical variation cannot validate its semantics, and outcome
performance must not be used after the fact to infer that the mapping was
correct.

### Evidence required

Approval requires authoritative protocol evidence establishing:

1. what each reward-array element represents during an active round;
2. whether index `i` corresponds to candidate square `i`;
3. when reward values become populated or acquire finalized meaning;
4. that the frozen value is available before the chosen decision point; and
5. deterministic agreement between the protocol definition, decoder, Replay
   projection, and candidate association.

If square-index semantics are disproven, per-square reward features must be
rejected rather than reinterpreted. A different whole-array use would be new
feature engineering and is outside this resolution.

### Decision

**Deferred.**

### Justification

The current authority establishes temporal presence but not candidate-square
semantics. The required protocol proof is absent from Discovery Sessions 1–4
and the Phase 1 audit. No reward-derived feature is eligible for RQ-003 until a
separate reviewed semantic audit resolves this class.

## 7. Cadence-sensitive temporal differences

### Class membership

This class contains existing deployment- and miner-derived values computed from
one or more adjacent observation indices:

- `miner_delta_1`, `miner_delta_2`, and `miner_delta_3`;
- `deployed_delta_1`, `deployed_delta_2`, and `deployed_delta_3`;
- `miner_momentum_3`, `miner_momentum_1`, and
  `miner_acceleration_1`;
- `deployed_momentum_3`, `deployed_momentum_1`, and
  `deployed_acceleration_1`;
- `miner_influx_rate_1`, `miner_outflow_rate_1`,
  `deployed_influx_rate_1`, and `deployed_outflow_rate_1`;
- `miner_board_change_volatility` and
  `deployed_board_change_volatility`; and
- `board_total_miner_delta_1` and `board_total_deployed_delta_1`.

Reward-derived members with analogous formulas remain governed by Section 6.

### Governing concern

RQ-003 permits deterministic same-round history but requires specific scrutiny
for exact transition counts, synchronization, and concentration because they
are cadence-sensitive. Cadence is a validation control and may not become a
candidate signal.

### Architectural concern

The current outputs use observation-index lags rather than a uniform protocol-
time interval. A change between adjacent records represents the endpoint
difference across whatever wall-clock and slot interval the observer happened
to capture.

### Research concern

Discovery Session 4 found a median maximum gap of about 1.01 seconds in the
dense group and 25.32 seconds in the sparse group. Sparse sampling increased
median largest-transition shares and reduced visible ordering transitions.
Therefore the class mixes protocol movement with the collection interval.

### Evidence required

Approval requires a pre-outcome cadence-stability analysis that:

- declares cadence strata without using winning outcomes;
- compares feature availability and distributions across those strata;
- separates initially zero from initially nonzero lifecycles where relevant;
- demonstrates that the exact candidate semantics remain comparable across the
  populations intended for evaluation;
- defines fail-closed treatment of missing exact lags; and
- does not expose cadence labels or availability flags to the ranking
  procedure.

The analysis must resolve the complete class or a predeclared subclass before
outcome evaluation. A favorable predictive result is not eligibility evidence.

### Decision

**Deferred.**

### Justification

The temporal direction is valid and all inputs precede the freeze, but the
existing evidence proves material cadence influence rather than stability. The
class is not categorically forbidden because RQ-003 allows audited same-round
history. It remains ineligible until the required cadence-stability evidence
exists.

## 8. Observation-count and availability features

### Class membership

- `has_previous_observation`;
- `has_history_2`;
- `has_history_3`;
- `has_rolling_window_3`;
- `has_momentum_1`;
- `has_previous_board_observation`;
- `observation_index`;
- `round_observation_count`; and
- `round_progress` as implemented from observation index and final observation
  count.

Phase 1 already classified these values as prohibited. They are included here
because their underlying question also controls fallback behavior in several
conditional temporal classes.

### Governing concern

RQ-003 makes cadence and lifecycle completeness audit controls, not candidate
signals. It also prohibits completed-lifecycle future information.

### Architectural concern

The `has_*` values reveal whether the observer captured particular lags or
windows. `round_observation_count` requires the completed lifecycle, and
`round_progress` uses that future total. These values describe the data-
collection path rather than an ORE account state.

### Research concern

Discovery Session 4 establishes that observation density and spacing are
measurement properties associated with chronology and capture regime. A
ranking procedure could learn the collector regime through these values.

### Evidence required

No additional descriptive evidence is required. Their definitions establish
the disallowed information channel. A future protocol-relative position value
would belong to the approved relative-timing class, not this class.

### Decision

**Rejected.**

### Justification

The class directly encodes cadence, coverage, or completed-lifecycle future
information. It may be retained for audit, missingness accounting, and
fail-closed computation, but it may not enter a predictive candidate schema.
Fallback values must not be made distinguishable to a candidate by supplying
these flags.

## 9. Historical rolling-window features

### Class membership

- `miner_rolling_mean_2`, `miner_rolling_mean_3`,
  `deployed_rolling_mean_2`, and `deployed_rolling_mean_3`;
- `miner_ema_0_5` and `deployed_ema_0_5`; and
- `miner_rolling_std_3` and `deployed_rolling_std_3`.

Reward rolling features remain governed by Section 6.

### Governing concern

RQ-003 allows deterministic same-round history, but the history must remain
comparable across collection regimes and cannot use cadence as a candidate
signal.

### Architectural concern

The current windows are defined by counts of retained observations, not by
slots or elapsed protocol time. Two nominal three-observation windows can span
about two seconds in a dense lifecycle or tens of seconds around a collection
gap. The EMA similarly assigns weight by observation position.

### Research concern

The archived data contains distinct cadence regimes. Discovery Session 4 shows
that endpoint movement accumulates across sparse intervals. A rolling summary
can therefore measure different protocol-time spans under the same column name.

### Evidence required

The cadence-stability analysis in Section 7 must additionally show:

- the actual slot and wall-clock spans represented by each window;
- feature availability and fallback frequency by cadence and lifecycle-start
  stratum;
- whether the intended comparison population has sufficiently comparable
  windows; and
- that no completed-lifecycle count or later observation enters the window.

### Decision

**Deferred.**

### Justification

All inputs can precede the freeze, so the class is not future information.
However, current evidence does not establish a stable meaning for fixed
observation-count windows across the intended population. No historical
rolling-window feature is eligible until that proof exists.

## 10. Leader persistence features

### Class membership

Deployment- and miner-derived:

- `miner_observations_since_leader_change` and
  `deployed_observations_since_leader_change`;
- `miner_leader_persistence` and `deployed_leader_persistence`;
- `miner_observations_since_became_leader` and
  `deployed_observations_since_became_leader`;
- `miner_consecutive_leader_observations` and
  `deployed_consecutive_leader_observations`; and
- `has_miner_ever_led` and `has_deployed_ever_led`.

Reward-leader outputs remain governed by Section 6.

### Governing concern

Snapshot-level leadership is approved protocol state, but historical
persistence must not be confused with observer persistence. RQ-003 requires
cadence and lifecycle-start controls.

### Architectural concern

The existing fields reconstruct leadership over retained observation indices.
They stop across noncontiguous history, count samples rather than protocol
time, and depend on which first state the lifecycle retained.

### Research concern

Discovery Session 4 supports instantaneous leaders and the broad distinction
between leader stability and lower-order movement. It does not support exact
leader-change counts as intrinsic. Sparse rounds show fewer visible miner
leader changes, and initially zero lifecycles begin with a 25-way tie that
necessarily alters later persistence histories.

### Evidence required

Approval requires a pre-outcome stability analysis that:

- separates dense and sparse cadence;
- separates initially zero and initially nonzero lifecycles;
- measures truncation at missing/noncontiguous history;
- distinguishes instantaneous leader membership from sampled persistence; and
- establishes which exact persistence outputs, if any, have comparable meaning
  across the intended evaluation population.

Availability and exact observation-count fields cannot be used as companion
signals. The `has_*_ever_led` booleans remain part of this deferred class
because lifecycle entry determines how much history “ever” covers.

### Decision

**Deferred.**

### Justification

The underlying leadership states are legitimate, but the historical duration
and “ever” semantics remain jointly influenced by cadence and lifecycle entry.
Current evidence neither approves nor categorically prohibits the class. Exact
observation-count availability signals remain rejected under Section 8.

## 11. Earlier-round deterministic state

### Class membership

- `prior_round_deterministic_state`, the architectural authorization class
  recorded in Phase 1.

No concrete feature currently belongs to this class.

### Governing concern

RQ-003 allows state derived from earlier completed rounds only after each prior
outcome has crossed RFC-010's revelation boundary. It does not authorize an
undefined state surface.

### Architectural concern

Any state must be immutable for the current decision, updated strictly in
chronological order, deterministic, reproducible from earlier rounds, and
unable to read the current or future outcome. No concrete identity, inputs,
update rule, missing-outcome rule, or initial state is presently specified.

### Research concern

An unspecified state can become an unrestricted channel for later-round
statistics, outcome availability, chronology, or procedure selection. Its
eligibility cannot be inferred from the fact that earlier outcomes may
legitimately be revealed.

### Evidence required

A future named state class would require a separate audit specifying:

- exact input fields;
- immutable initial state;
- deterministic update and ordering rules;
- treatment of missing outcomes and skipped rounds;
- proof that only earlier outcome-revealed rounds contribute;
- component and state identities;
- reproduction across chronological replay; and
- exclusion of capture mode, provenance, collection identity, and accidental
  chronology signals from the candidate surface.

Defining any of these would be feature engineering and is outside Phase 2.

### Decision

**Deferred.**

### Justification

The architecture permits a future audited class, but there is no concrete
feature to approve. Blanket approval would evade the Phase 1 requirement that
every concrete input receive a named audit.

## 12. Complete Phase 1 conditional mapping

This matrix confirms that every conditional category in Phase 1 has one
governing Phase 2 disposition.

| Phase 1 conditional category | Phase 2 owner | Decision |
|---|---|---|
| Absolute `start_slot`, `end_slot`, Board aliases, and `expires_at` | Section 3 | Rejected |
| Relative `slots_elapsed` and `slots_remaining` timing distinction | Section 4 | Approved |
| Pre-finalization `total_vaulted` and `total_winnings` | Section 5 | Approved |
| Raw and per-candidate reward semantics | Section 6 | Deferred |
| Reward temporal and reward-leader outputs | Section 6 | Deferred |
| Miner/deployment lag deltas, momentum, acceleration, influx/outflow, board volatility, and board-total deltas | Section 7 | Deferred |
| Observation-history availability and completed-lifecycle count/progress values | Section 8 | Rejected |
| Miner/deployment rolling means, EMA, and rolling standard deviation | Section 9 | Deferred |
| Miner/deployment leader age, persistence, prior leadership, and ever-led state | Section 10 | Deferred |
| Unspecified earlier-round deterministic state | Section 11 | Deferred |

No Phase 1 conditional class is implicitly approved by omission.

## 13. Final disposition

### Approved feature classes

- **Relative protocol timing:** `slots_elapsed` and `slots_remaining` at the
  frozen decision context, preserving genuine unavailability.
- **Pre-finalization Round aggregates:** contemporaneous
  `round.total_vaulted` and `round.total_winnings` from the selected normal
  observation only.

Approval means information-boundary eligibility. It does not assert usefulness
and does not authorize implementation or outcome evaluation.

### Rejected feature classes

- **Absolute protocol timing and slot identity:** raw start, end, expiry, RPC,
  or equivalent absolute slot values as candidate inputs.
- **Observation-count, window-availability, cadence, and completed-lifecycle
  position signals:** including all `has_*` availability flags,
  `observation_index`, `round_observation_count`, and observation-count-derived
  `round_progress`.

Rejected values may remain structural, computational, or audit metadata. They
may not enter the RQ-003 predictive candidate surface.

### Deferred feature classes

- **Reward-derived features**, pending authoritative reward-array semantic and
  pre-finalization evidence.
- **Cadence-sensitive temporal differences**, pending a pre-outcome stability
  analysis across collection regimes and lifecycle starts.
- **Historical rolling-window features**, pending proof that fixed
  observation-count windows have comparable meaning in the intended
  population.
- **Leader persistence features**, pending cadence, lifecycle-entry, and
  truncation stability evidence.
- **Earlier-round deterministic state**, pending a concrete named state class
  and separate leakage audit.

Deferred classes are ineligible unless and until the named evidence is produced
and reviewed. A favorable outcome association cannot supply the missing
eligibility proof.

## 14. Phase 2 conclusion

Phase 2 resolves the entire conditional surface without selecting or
constructing a feature set. Later RQ-003 work may use Phase 1 features already
marked **Yes** and the two approved classes above. It must exclude rejected
classes and must not use deferred classes until their specified evidence exists
and a reviewed resolution changes their status.
