# RQ-003 Phase 1 — Decision-Time Feature Audit

## Status

**Type:** Research protocol deliverable

**Phase:** RQ-003 Phase 1

**Scope:** Decision-time feature eligibility only

**Implementation authorized:** No

This audit inventories information already exposed at the RQ-003 decision
boundary and the repository's existing deterministic feature vocabulary. It
does not evaluate usefulness, engineer a feature, rank a feature, propose a
model, or authorize implementation.

## Authority

This audit is governed by:

- [RQ-003 — Decision-Time Winning-Square Information](RQ-003-winning-square-predictability.md);
- [Discovery Session 1 — Dataset Inventory](../notebook/discovery-session-001.md);
- [Discovery Session 2 — Round Evolution](../notebook/discovery-session-002.md);
- [Discovery Session 3 — Round Taxonomy](../notebook/discovery-session-003.md); and
- [Discovery Session 4 — Behavioral Dimensions](../notebook/discovery-session-004.md).

The implementation was inspected only to identify the exact immutable
`DecisionContext` projection and the names and formulas of already existing
feature outputs. Implementation presence does not establish RQ-003 eligibility.

## Audit vocabulary

The tables use the following eligibility values:

- **Yes:** eligible under the current RQ-003 information boundary.
- **Conditional:** temporally eligible, but use requires the named semantic,
  chronology, cadence, or pre-finalization validation before evaluation.
- **No:** prohibited as a predictive input under RQ-003.
- **Not a feature:** permitted only as a key, control, label, or audit value.

“Historical observations” means normal observations at or before the frozen
decision observation or state from earlier outcome-revealed rounds. It never
includes a later observation from the current round.

## Decision-time freeze boundary

The authoritative freeze occurs when Replay selects the latest eligible normal
observation at or before the predeclared decision point and constructs the
deeply immutable `DecisionContext`.

An eligible candidate may consume only:

- the frozen `DecisionContext`;
- normal observations of the same round no later than that context;
- fixed configuration declared before evaluation; and
- deterministic state derived from earlier completed rounds only after their
  outcomes crossed RFC-010's revelation boundary.

Current-round finalized evidence, RFC-012 evidence, enrichment, and later
normal observations remain outside this boundary. A field that is physically
present in an account is eligible only at the value recorded in the frozen,
pre-finalization observation.

## 1. Raw Decision-Time Features

The source is the immutable Strategy Lab `DecisionContext` projection in
[`strategy_lab/runner.py`](../../../src/orev3/strategy_lab/runner.py) and its
normalized Replay point. Vector notation `[0..24]` inventories all 25 elements
individually under one shared contract.

| Name | Source | Description | Decision-time availability | Deterministic? | Requires historical observations? | Eligible under RQ-003? | Reason if prohibited or conditional |
|---|---|---|---|---|---|---|---|
| `round_id` | Replay point | Current protocol round identity | Present at freeze | Yes | No | Not a feature | Structural join key and accidental identity/chronology proxy; prohibited as predictive input |
| `observed_at_utc` | Normal snapshot envelope | Wall-clock observation timestamp | Present at freeze | Yes | No | No | Timestamp and chronology proxy explicitly prohibited |
| `rpc_slot` | Normal snapshot envelope | Absolute RPC context slot | Present at freeze | Yes | No | No | Absolute chronology proxy; may support eligible timing derivations but is not itself a predictive input |
| `start_slot` | Selected Board state | Current round start slot | Present at freeze | Yes | No | Conditional | RQ-003 permits protocol timing, but direct use must pass the accidental-chronology-proxy audit |
| `end_slot` | Selected Board state | Current round end slot, or unavailable during initialization | Present when protocol state supplies it | Yes | No | Conditional | Eligible protocol timing only with explicit missingness handling and chronology-proxy audit |
| `slots_elapsed` | Replay derivation | `max(rpc_slot - start_slot, 0)` | Derived entirely at freeze | Yes | No | Yes | — |
| `slots_remaining` | Replay derivation | `max(end_slot - rpc_slot, 0)`, unavailable during initialization | Derived at freeze when `end_slot` exists | Yes | No | Yes | — |
| `board.round_id` | Selected Board state | Board-selected round identity | Present at freeze | Yes | No | Not a feature | Redundant structural identity and prohibited identity/chronology proxy |
| `board.start_slot` | Selected Board state | Raw Board start-slot value | Present at freeze | Yes | No | Conditional | Same timing value as `start_slot`; chronology-proxy and duplicate-input audit required |
| `board.end_slot` | Selected Board state | Raw Board end-slot value, including protocol initialization semantics | Present at freeze | Yes | No | Conditional | Same timing source as `end_slot`; missingness, chronology-proxy, and duplicate-input audit required |
| `board.production_cost_ema` | Selected Board state | Contemporaneous Board production-cost exponential moving average | Present when supplied by the source schema | Yes | No | Yes | — |
| `treasury.motherlode` | Selected Treasury state | Contemporaneous Treasury motherlode | Present at freeze | Yes | No | Yes | — |
| `round.round_id` | Selected Round account | Round-account identity | Present at freeze | Yes | No | Not a feature | Redundant structural identity and prohibited identity/chronology proxy |
| `round.deployed_lamports[0..24]` | Selected Round account | Twenty-five contemporaneous square deployment amounts | Present at freeze | Yes | No | Yes | — |
| `round.miner_counts[0..24]` | Selected Round account | Twenty-five contemporaneous square miner counts | Present at freeze | Yes | No | Yes | — |
| `round.rewards[0..24]` | Selected Round account | Raw 25-element protocol reward array at the frozen observation | Present at freeze | Yes | No | Conditional | Whole contemporaneous array is boundary-eligible; repository semantics do not establish that array indices map to board squares, and finalized values remain prohibited |
| `round.expires_at` | Selected Round account | Round-account expiry slot | Present at freeze | Yes | No | Conditional | Contemporaneous protocol state, but an absolute-slot chronology-proxy audit is required |
| `round.motherlode` | Selected Round account | Round motherlode value at the frozen observation | Present at freeze | Yes | No | Yes | Finalized value from a later observation remains prohibited |
| `round.total_vaulted` | Selected Round account | Total vaulted value at the frozen observation | Present at freeze | Yes | No | Conditional | Eligible only when the selected context is proven pre-finalization; finalized outcome value is prohibited |
| `round.total_winnings` | Selected Round account | Total winnings value at the frozen observation | Present at freeze | Yes | No | Conditional | Eligible only when the selected context is proven pre-finalization; finalized outcome value is prohibited |
| `round.total_miners` | Selected Round account | Protocol total-miner count at the frozen observation | Present at freeze | Yes | No | Yes | — |
| `round.top_miner` | Selected Round account | Top-miner account identity at the frozen observation | Present at freeze | Yes | No | No | Account identity is an accidental identity signal; finalized top-miner value is also outcome information |
| `square_identifier` | Candidate-set structure | Identity of one of the 25 candidates | Structurally present for ranking | Yes | No | Not a feature | Required as the candidate key and baseline ordering key, but not authorized as a predictive input by this audit |

### Raw fields outside `DecisionContext`

The normalized raw snapshot also contains `collector_session_id`,
`source_file`, and `source_line_number`, and the raw Round account contains
`mass`, `slot_hash_hex`, and `entropy`. Their omission from `DecisionContext` is
intentional. They are inventoried as prohibited values in Section 4 rather
than raw candidates.

## 2. Derived Decision-Time Features

These are existing deterministic, current-observation outputs in the repository
feature registry. They use no earlier observation. Their source formulas are in
[`features/raw.py`](../../../src/orev3/features/raw.py) and
[`features/relative.py`](../../../src/orev3/features/relative.py).

| Name | Source | Description | Decision-time availability | Deterministic? | Requires historical observations? | Eligible under RQ-003? | Reason if prohibited or conditional |
|---|---|---|---|---|---|---|---|
| `miner_count` | `round.miner_counts[square]` | Current miner count for the candidate square | At freeze | Yes | No | Yes | — |
| `deployed_lamports` | `round.deployed_lamports[square]` | Current deployed lamports for the candidate square | At freeze | Yes | No | Yes | — |
| `reward_raw` | `round.rewards[square]` in the existing feature pipeline | Current raw reward-array element assigned to the candidate index | At freeze | Yes | No | Conditional | Requires proof that reward-array indices have square semantics; later finalized reward values are prohibited |
| `miner_share` | Current 25-square miner vector | Candidate miner count divided by current board miner total; zero when total is nonpositive | At freeze | Yes | No | Yes | — |
| `deployed_share` | Current 25-square deployment vector | Candidate deployment divided by current board deployment total; zero when total is nonpositive | At freeze | Yes | No | Yes | — |
| `miner_average_rank` | Current 25-square miner vector | One-based descending average rank with exact ties sharing their average rank | At freeze | Yes | No | Yes | — |
| `deployed_average_rank` | Current 25-square deployment vector | One-based descending average rank with exact ties sharing their average rank | At freeze | Yes | No | Yes | — |
| `miner_ratio_to_leader` | Current 25-square miner vector | Candidate miner count divided by the current maximum; zero for nonpositive denominator | At freeze | Yes | No | Yes | — |
| `deployed_ratio_to_leader` | Current 25-square deployment vector | Candidate deployment divided by the current maximum; zero for nonpositive denominator | At freeze | Yes | No | Yes | — |
| `miner_ratio_to_mean` | Current 25-square miner vector | Candidate miner count divided by the current arithmetic mean; zero for nonpositive denominator | At freeze | Yes | No | Yes | — |
| `deployed_ratio_to_mean` | Current 25-square deployment vector | Candidate deployment divided by the current arithmetic mean; zero for nonpositive denominator | At freeze | Yes | No | Yes | — |
| `miner_difference_from_mean` | Current 25-square miner vector | Candidate miner count minus the current board mean | At freeze | Yes | No | Yes | — |
| `deployed_difference_from_mean` | Current 25-square deployment vector | Candidate deployment minus the current board mean | At freeze | Yes | No | Yes | — |
| `miner_z_score` | Current 25-square miner vector | Population-standardized current miner count; zero when board standard deviation is nonpositive | At freeze | Yes | No | Yes | — |
| `deployed_z_score` | Current 25-square deployment vector | Population-standardized current deployment; zero when board standard deviation is nonpositive | At freeze | Yes | No | Yes | — |

The totals, means, standard deviations, leaders, and tie-aware ranks used by
these outputs are deterministic intermediates, not additional registered
candidate features. Listing their resulting registered outputs above does not
authorize new summary features.

## 3. Historical Decision-Time Features

These outputs already exist in the repository's temporal feature registry.
They use only the current square or board and normal observations earlier in
the same round. The implementation requires ordered histories, rejects future
observation indices, and stops contiguous-history calculations at gaps.

“Conditional” below means temporally eligible but subject to RQ-003's
predeclared cadence-stability audit. Discovery Session 4 established that exact
transition counts and adjacent-observation dynamics change with sampling
cadence. Availability flags that directly expose observation coverage are
prohibited rather than conditional.

### 3.1 Fixed-lag changes

| Name | Source | Description | Decision-time availability | Deterministic? | Requires historical observations? | Eligible under RQ-003? | Reason if prohibited or conditional |
|---|---|---|---|---|---|---|---|
| `miner_delta_1` | Current and immediately previous contiguous square observations | One-observation miner-count difference | When lag 1 exists; otherwise repository fallback is zero | Yes | Yes | Conditional | Adjacent-observation magnitude is cadence-sensitive; stability audit required |
| `deployed_delta_1` | Current and immediately previous contiguous square observations | One-observation deployment difference | When lag 1 exists; otherwise zero fallback | Yes | Yes | Conditional | Cadence-stability audit required |
| `reward_delta_1` | Current and immediately previous contiguous raw reward elements | One-observation reward-array difference | When lag 1 exists; otherwise zero fallback | Yes | Yes | Conditional | Reward-index semantics and cadence stability must both be proven |
| `has_previous_observation` | Same-round observation availability | Boolean indicating presence of lag 1 | At freeze | Yes | Yes | No | Direct observation-coverage/cadence signal prohibited as predictive input |
| `miner_delta_2` | Current and lag-2 square observations | Miner-count difference across two observation indices | When exact lag 2 exists; otherwise zero fallback | Yes | Yes | Conditional | Observation-index lag is cadence-sensitive; stability audit required |
| `deployed_delta_2` | Current and lag-2 square observations | Deployment difference across two observation indices | When exact lag 2 exists; otherwise zero fallback | Yes | Yes | Conditional | Cadence-stability audit required |
| `reward_delta_2` | Current and lag-2 raw reward elements | Reward-array difference across two observation indices | When exact lag 2 exists; otherwise zero fallback | Yes | Yes | Conditional | Reward-index semantics and cadence stability must both be proven |
| `has_history_2` | Same-round observation availability | Boolean indicating presence of exact lag 2 | At freeze | Yes | Yes | No | Direct observation-coverage/cadence signal prohibited as predictive input |
| `miner_delta_3` | Current and lag-3 square observations | Miner-count difference across three observation indices | When exact lag 3 exists; otherwise zero fallback | Yes | Yes | Conditional | Observation-index lag is cadence-sensitive; stability audit required |
| `deployed_delta_3` | Current and lag-3 square observations | Deployment difference across three observation indices | When exact lag 3 exists; otherwise zero fallback | Yes | Yes | Conditional | Cadence-stability audit required |
| `reward_delta_3` | Current and lag-3 raw reward elements | Reward-array difference across three observation indices | When exact lag 3 exists; otherwise zero fallback | Yes | Yes | Conditional | Reward-index semantics and cadence stability must both be proven |
| `has_history_3` | Same-round observation availability | Boolean indicating presence of exact lag 3 | At freeze | Yes | Yes | No | Direct observation-coverage/cadence signal prohibited as predictive input |

### 3.2 Rolling and change dynamics

| Name | Source | Description | Decision-time availability | Deterministic? | Requires historical observations? | Eligible under RQ-003? | Reason if prohibited or conditional |
|---|---|---|---|---|---|---|---|
| `miner_rolling_mean_2` | Up to two trailing contiguous square observations | Arithmetic mean of miner counts | At freeze from available trailing history | Yes | Yes | Conditional | Window is observation-count based; cadence-stability audit required |
| `deployed_rolling_mean_2` | Up to two trailing contiguous square observations | Arithmetic mean of deployment | At freeze from available trailing history | Yes | Yes | Conditional | Cadence-stability audit required |
| `reward_rolling_mean_2` | Up to two trailing contiguous raw reward elements | Arithmetic mean of reward elements | At freeze from available trailing history | Yes | Yes | Conditional | Reward-index semantics and cadence stability must both be proven |
| `miner_rolling_mean_3` | Up to three trailing contiguous square observations | Arithmetic mean of miner counts | At freeze from available trailing history | Yes | Yes | Conditional | Window is observation-count based; cadence-stability audit required |
| `deployed_rolling_mean_3` | Up to three trailing contiguous square observations | Arithmetic mean of deployment | At freeze from available trailing history | Yes | Yes | Conditional | Cadence-stability audit required |
| `reward_rolling_mean_3` | Up to three trailing contiguous raw reward elements | Arithmetic mean of reward elements | At freeze from available trailing history | Yes | Yes | Conditional | Reward-index semantics and cadence stability must both be proven |
| `miner_ema_0_5` | Full trailing contiguous square history | Miner-count exponential moving average with fixed alpha `0.5` | At freeze | Yes | Yes | Conditional | Observation-cadence weighting must pass stability audit |
| `deployed_ema_0_5` | Full trailing contiguous square history | Deployment exponential moving average with fixed alpha `0.5` | At freeze | Yes | Yes | Conditional | Observation-cadence weighting must pass stability audit |
| `reward_ema_0_5` | Full trailing contiguous raw reward history | Reward-element exponential moving average with fixed alpha `0.5` | At freeze | Yes | Yes | Conditional | Reward-index semantics and cadence stability must both be proven |
| `miner_momentum_3` | Up to four trailing contiguous square observations | Mean miner-count difference over as many as three available transitions | At freeze | Yes | Yes | Conditional | Transition count is cadence-sensitive; stability audit required |
| `deployed_momentum_3` | Up to four trailing contiguous square observations | Mean deployment difference over as many as three available transitions | At freeze | Yes | Yes | Conditional | Cadence-stability audit required |
| `reward_momentum_3` | Up to four trailing contiguous raw reward observations | Mean reward-element difference over as many as three transitions | At freeze | Yes | Yes | Conditional | Reward-index semantics and cadence stability must both be proven |
| `miner_acceleration_1` | Three trailing contiguous square observations | Current miner count minus twice lag 1 plus lag 2 | At freeze; zero when fewer than three observations | Yes | Yes | Conditional | Second difference is cadence-sensitive; stability audit required |
| `deployed_acceleration_1` | Three trailing contiguous square observations | Current deployment minus twice lag 1 plus lag 2 | At freeze; zero when fewer than three observations | Yes | Yes | Conditional | Cadence-stability audit required |
| `reward_acceleration_1` | Three trailing contiguous raw reward observations | Current reward element minus twice lag 1 plus lag 2 | At freeze; zero when fewer than three observations | Yes | Yes | Conditional | Reward-index semantics and cadence stability must both be proven |
| `miner_influx_rate_1` | Current and lag-1 square observations | Positive part of one-observation miner-count difference | At freeze; zero without lag 1 | Yes | Yes | Conditional | Observation-based “rate” is cadence-sensitive; stability audit required |
| `miner_outflow_rate_1` | Current and lag-1 square observations | Positive part of the negated one-observation miner-count difference | At freeze; zero without lag 1 | Yes | Yes | Conditional | Observation-based “rate” is cadence-sensitive; stability audit required |
| `deployed_influx_rate_1` | Current and lag-1 square observations | Positive part of one-observation deployment difference | At freeze; zero without lag 1 | Yes | Yes | Conditional | Observation-based “rate” is cadence-sensitive; stability audit required |
| `deployed_outflow_rate_1` | Current and lag-1 square observations | Positive part of the negated one-observation deployment difference | At freeze; zero without lag 1 | Yes | Yes | Conditional | Observation-based “rate” is cadence-sensitive; stability audit required |

### 3.3 Leadership and board dynamics

| Name | Source | Description | Decision-time availability | Deterministic? | Requires historical observations? | Eligible under RQ-003? | Reason if prohibited or conditional |
|---|---|---|---|---|---|---|---|
| `miner_observations_since_leader_change` | Ordered same-round board history | Age in contiguous observations of the current miner-leader set | At freeze | Yes | Yes | Conditional | Exact observation count is cadence-sensitive; stability audit required |
| `deployed_observations_since_leader_change` | Ordered same-round board history | Age in contiguous observations of the current deployment-leader set | At freeze | Yes | Yes | Conditional | Exact observation count is cadence-sensitive; stability audit required |
| `miner_leader_persistence` | Ordered same-round board history and candidate square | Consecutive observations in which the candidate remains a miner leader | At freeze | Yes | Yes | Conditional | Exact observation count is cadence-sensitive; stability audit required |
| `deployed_leader_persistence` | Ordered same-round board history and candidate square | Consecutive observations in which the candidate remains a deployment leader | At freeze | Yes | Yes | Conditional | Exact observation count is cadence-sensitive; stability audit required |
| `miner_board_change_volatility` | Current and exact lag-1 board vectors | Population standard deviation across the 25 one-observation miner-count changes | At freeze; zero without lag-1 board | Yes | Yes | Conditional | Adjacent-observation changes are cadence-sensitive; stability audit required |
| `deployed_board_change_volatility` | Current and exact lag-1 board vectors | Population standard deviation across the 25 one-observation deployment changes | At freeze; zero without lag-1 board | Yes | Yes | Conditional | Cadence-stability audit required |

### 3.4 Additional existing temporal outputs

| Name | Source | Description | Decision-time availability | Deterministic? | Requires historical observations? | Eligible under RQ-003? | Reason if prohibited or conditional |
|---|---|---|---|---|---|---|---|
| `miner_rolling_std_3` | Up to three trailing contiguous square observations | Population standard deviation of miner counts | At freeze | Yes | Yes | Conditional | Observation-window and fallback semantics require cadence-stability audit |
| `deployed_rolling_std_3` | Up to three trailing contiguous square observations | Population standard deviation of deployment | At freeze | Yes | Yes | Conditional | Cadence-stability audit required |
| `reward_rolling_std_3` | Up to three trailing contiguous raw reward elements | Population standard deviation of reward elements | At freeze | Yes | Yes | Conditional | Reward-index semantics and cadence stability must both be proven |
| `has_rolling_window_3` | Same-round observation availability | Boolean indicating exactly three contiguous trailing observations were available | At freeze | Yes | Yes | No | Direct observation-coverage/cadence signal prohibited as predictive input |
| `miner_momentum_1` | Three trailing contiguous square observations | Existing implementation's one-step second difference for miner count | At freeze; zero without three observations | Yes | Yes | Conditional | Cadence-sensitive second difference; stability audit required |
| `deployed_momentum_1` | Three trailing contiguous square observations | Existing implementation's one-step second difference for deployment | At freeze; zero without three observations | Yes | Yes | Conditional | Cadence-stability audit required |
| `reward_momentum_1` | Three trailing contiguous raw reward observations | Existing implementation's one-step second difference for reward element | At freeze; zero without three observations | Yes | Yes | Conditional | Reward-index semantics and cadence stability must both be proven |
| `has_momentum_1` | Same-round observation availability | Boolean indicating the three-observation input was available | At freeze | Yes | Yes | No | Direct observation-coverage/cadence signal prohibited as predictive input |
| `miner_observations_since_became_leader` | Ordered same-round board history and candidate square | Implementation-defined observation count relative to the candidate's most recent miner-leadership boundary | At freeze | Yes | Yes | Conditional | Exact observation count is cadence-sensitive; stability audit required |
| `miner_consecutive_leader_observations` | Ordered same-round board history and candidate square | Current consecutive observations as a miner leader | At freeze | Yes | Yes | Conditional | Exact observation count is cadence-sensitive; stability audit required |
| `has_miner_ever_led` | Ordered same-round board history and candidate square | Whether the candidate has appeared in a miner-leader set by the freeze | At freeze | Yes | Yes | Conditional | Historical leader state is eligible, but coverage/cadence stability must be audited |
| `deployed_observations_since_became_leader` | Ordered same-round board history and candidate square | Implementation-defined observation count relative to the candidate's most recent deployment-leadership boundary | At freeze | Yes | Yes | Conditional | Exact observation count is cadence-sensitive; stability audit required |
| `deployed_consecutive_leader_observations` | Ordered same-round board history and candidate square | Current consecutive observations as a deployment leader | At freeze | Yes | Yes | Conditional | Exact observation count is cadence-sensitive; stability audit required |
| `has_deployed_ever_led` | Ordered same-round board history and candidate square | Whether the candidate has appeared in a deployment-leader set by the freeze | At freeze | Yes | Yes | Conditional | Historical leader state is eligible, but coverage/cadence stability must be audited |
| `reward_observations_since_became_leader` | Ordered same-round board history and candidate index | Implementation-defined observation count relative to the indexed reward leader boundary | At freeze | Yes | Yes | Conditional | Reward-index square semantics and cadence stability must both be proven |
| `reward_consecutive_leader_observations` | Ordered same-round board history and candidate index | Current consecutive observations as an indexed reward leader | At freeze | Yes | Yes | Conditional | Reward-index square semantics and cadence stability must both be proven |
| `has_reward_ever_led` | Ordered same-round board history and candidate index | Whether the candidate index has appeared in an indexed reward-leader set | At freeze | Yes | Yes | Conditional | Reward-index square semantics and coverage/cadence stability must be proven |
| `board_total_miner_delta_1` | Current and exact lag-1 board vectors | One-observation difference in total square miner counts | At freeze; zero without lag-1 board | Yes | Yes | Conditional | Adjacent-observation aggregate is cadence-sensitive; stability audit required |
| `board_total_deployed_delta_1` | Current and exact lag-1 board vectors | One-observation difference in total square deployment | At freeze; zero without lag-1 board | Yes | Yes | Conditional | Cadence-stability audit required |
| `has_previous_board_observation` | Same-round board-observation availability | Boolean indicating presence of exact lag-1 board state | At freeze | Yes | Yes | No | Direct observation-coverage/cadence signal prohibited as predictive input |

### 3.5 Earlier-round deterministic state

RQ-003 permits deterministic state derived from earlier completed rounds only
after their outcomes have crossed RFC-010's outcome-revelation boundary. No
concrete earlier-round feature is specified by RQ-003 or the Discovery
Sessions. Therefore this audit records the authorization class but approves no
named prior-round candidate.

| Name | Source | Description | Decision-time availability | Deterministic? | Requires historical observations? | Eligible under RQ-003? | Reason if prohibited or conditional |
|---|---|---|---|---|---|---|---|
| `prior_round_deterministic_state` | Earlier completed, outcome-revealed rounds only | Architectural authorization for future audited state, not a concrete feature | Before the current decision if updated strictly in chronology | Required | Yes, across rounds | Not a feature | Any concrete state definition would be feature engineering and requires a separate named audit before evaluation |

## 4. Explicitly Prohibited Features

The following values may exist in raw data, lifecycle records, evaluation
records, or research metadata. Availability somewhere in the repository does
not place them inside the decision-time boundary.

| Name | Source | Description | Decision-time availability | Deterministic? | Requires historical observations? | Eligible under RQ-003? | Reason if prohibited |
|---|---|---|---|---|---|---|---|
| `winning_square` | Finalized outcome | Final winning square and evaluation label | Only after outcome revelation | Yes | No | No | Target leakage; label only |
| `won` | Feature/evaluation dataset label | Whether one candidate equals the winning square | Only after outcome revelation | Yes | No | No | Target leakage; label only |
| `entropy` | Finalized Round state | Final entropy from which the winner is derived | Only after finalization | Yes | No | No | Outcome information |
| Finalized `slot_hash_hex` or finalization indicator | Finalized Round state | Evidence that the round has finalized | Only after finalization for the relevant value | Yes | No | No | Outcome/future information relative to the decision |
| Finalized `rewards[0..24]` | Finalized Round state or outcome | Final reward array | Only after finalization | Yes | No | No | Outcome information |
| Finalized `total_vaulted` | Finalized Round state or outcome | Final total vaulted value | Only after finalization | Yes | No | No | Outcome information |
| Finalized `total_winnings` | Finalized Round state or outcome | Final total winnings | Only after finalization | Yes | No | No | Outcome information |
| Finalized `motherlode` | Finalized Round/Treasury outcome state | Final motherlode value unavailable at the decision | Only after finalization | Yes | No | No | Future/outcome information |
| Finalized `top_miner` | Finalized Round state or outcome | Final top-miner account | Only after finalization | Yes | No | No | Outcome information and account identity |
| Future observations | Normal snapshot stream after freeze | Any current-round snapshot later than the selected context | After decision | Yes | Yes | No | Direct future-information leakage |
| Final Board or Round state | Later normal or finalized snapshot | State not available at the selected decision | After decision | Yes | Yes | No | Future-information leakage |
| RFC-012 transition evidence | RFC-012 evidence stream | Transition, predecessor, response, payload, validation, or terminal evidence | Parsed only after normal snapshot freeze | Yes | No | No | Outcome-only evidence explicitly excluded from Replay and `DecisionContext` |
| RFC-012 evidence identities | Lifecycle outcome metadata | Immutable identities supporting post-transition capture | After decision | Yes | No | No | Outcome provenance, not strategy-visible information |
| Historical enrichment payload | Enrichment source | Outcome recovered after collection | After decision | Yes | No | No | Outcome-only information |
| `finalized_outcome_source` | Lifecycle record | `observed`, `enriched`, or missing source classification | Known through outcome assembly | Yes | No | No | Outcome availability/provenance control only |
| `finalized_outcome_capture_mode` | Lifecycle record | `current_round`, `post_transition_predecessor`, or null | Known through outcome assembly | Yes | No | No | Capture-mode control only |
| Current-round outcome availability | Lifecycle/evaluation record | Whether a finalized outcome eventually exists | Known after outcome assembly | Yes | No | No | Selection leakage; audit/control only |
| `coverage_status` | Lifecycle quality metadata | Complete or partial lifecycle classification | Known after lifecycle assembly | Yes | Yes | No | Lifecycle-control variable only; not a candidate signal |
| Observation cadence and gap summaries | Lifecycle quality or research analysis | Counts, spacing, maximum gaps, and density over retained observations | Often requires later lifecycle observations | Yes | Yes | No | Cadence is a validation stratum, not a predictive input |
| `collector_session_id` | Snapshot envelope | Observer process/session identity | Present in raw snapshot | Yes | No | No | Accidental collection-regime identity |
| `source_schema_version` | Snapshot envelope | Raw source schema identity | Present in raw snapshot | Yes | No | No | Collection-regime metadata, not protocol state |
| `source_file` | Replay/source reference | Raw source path | Present in repository data | Yes | No | No | Dataset-location and chronology leakage |
| `source_line_number` | Replay/source reference | One-based raw source line | Present in repository data | Yes | No | No | Dataset-location and chronology leakage |
| `round_id` aliases | Board, Round, Replay, lifecycle, or feature rows | Current round identity | Present | Yes | No | No | Structural join key and accidental chronology/identity proxy |
| Wall-clock timestamp | Snapshot or lifecycle metadata | Observation, first, last, creation, or outcome timestamp | Present in corresponding record | Yes | No | No | Chronology proxy; split/audit use only |
| Absolute `rpc_slot` | Snapshot envelope | Absolute chain slot | Present at freeze | Yes | No | No | Chronology proxy; derivation/audit use only |
| `observation_index` | Feature/dataset construction | Ordinal of a retained observation | Available to the builder | Yes | Yes | No | Direct observation-cadence and lifecycle-position signal not in `DecisionContext` |
| `round_observation_count` | Completed lifecycle/feature construction | Total retained observations in the round | Requires completed lifecycle | Yes | Yes | No | Future lifecycle information and cadence/coverage signal |
| `round_progress` | Existing `FeatureContext` | Observation index divided by final observation count minus one | Requires final observation count | Yes | Yes | No | Uses completed-lifecycle future information and cadence |
| `has_previous_observation` | Existing temporal feature | Exact lag-1 availability flag | At freeze from history | Yes | Yes | No | Direct cadence/coverage signal |
| `has_history_2` | Existing temporal feature | Exact lag-2 availability flag | At freeze from history | Yes | Yes | No | Direct cadence/coverage signal |
| `has_history_3` | Existing temporal feature | Exact lag-3 availability flag | At freeze from history | Yes | Yes | No | Direct cadence/coverage signal |
| `has_rolling_window_3` | Existing temporal feature | Three-observation window-availability flag | At freeze from history | Yes | Yes | No | Direct cadence/coverage signal |
| `has_momentum_1` | Existing temporal feature | Three-observation input-availability flag | At freeze from history | Yes | Yes | No | Direct cadence/coverage signal |
| `has_previous_board_observation` | Existing temporal feature | Exact lag-1 board-availability flag | At freeze from history | Yes | Yes | No | Direct cadence/coverage signal |
| `square_index` / raw square identifier | Candidate and feature row key | Structural identity of one candidate square | Present | Yes | No | No | Structural key under this audit; deterministic fixed ordering belongs to the required baseline, not the candidate feature surface |
| `top_miner` account identity | Selected or finalized Round state | Account/public-key identity | May be present at freeze | Yes | No | No | Accidental participant identity signal; finalized form is also outcome information |
| `mass[0..24]` | Raw Round account | Raw mass vector | Present in raw snapshot but omitted from `DecisionContext` | Yes | No | No | Repository audit finds constant zero mass and expressly prohibits predictive use |
| Replay selection internals | `ReplaySelection` | Requested slot, exact-match flag, slot distance, tolerance, or loader state | Available only through Replay internals | Yes | No | No | Replay implementation details unavailable during live inference |
| Dataset identity or hash | Dataset/experiment metadata | Dataset version, path, SHA-256, or creation identity | Available to research orchestration | Yes | No | No | Reproducibility metadata, not decision-time protocol state |
| Full-history statistics | Any calculation crossing the evaluation boundary | Aggregate using later rounds or the complete dataset future | Not available at historical decision | Possibly | Yes | No | Chronological leakage |
| Imputed outcome or winner | Any synthetic/repaired source | Guessed finalized fact | Never observed | Depends | No | No | RQ-003 prohibits fabrication and imputation |
| Deployment decision or allocation | RFC-010 downstream components | Ranked deployment or capital allocation | Produced after Strategy input | Yes | No | No | Downstream output, not decision-time input |
| Evaluation result | RFC-010 Evaluator | Hit, miss, rank outcome, or revealed winner | After decision | Yes | No | No | Outcome/evaluation information |
| RFC-011 economic state or result | Economics layer | Budget, fees, settlement, SOL/ORE result, or economic metric | Downstream of decision and outcome | Yes | Yes | No | RFC-011 is downstream and cannot establish RQ-003 information content |

## 5. Audit conclusions

### 5.1 Eligible without additional semantic qualification

The audited surface supports the following feature categories without crossing
the decision boundary:

- contemporaneous elapsed and remaining protocol timing;
- contemporaneous production-cost and Treasury state;
- current deployed-lamport and miner-count vectors;
- contemporaneous Round fields explicitly marked **Yes** in Section 1; and
- deterministic current-board deployment/miner shares, tie-aware ranks,
  ratios, differences, and standardized values.

This is an eligibility statement only. It makes no claim of usefulness.

### 5.2 Conditional candidates

The following require additional proof before entering an RQ-003 evaluation:

- absolute protocol slot fields require an accidental-chronology-proxy audit;
- `total_vaulted` and `total_winnings` require proof that the selected context
  is pre-finalization;
- reward-array candidates require protocol evidence that array indices have the
  square semantics assumed by the candidate feature;
- same-round historical dynamics require proof that every input observation is
  at or before the freeze, and all observation-count-based dynamics require the
  predeclared cadence-stability audit required by RQ-003; and
- any future concrete earlier-round state requires its own named feature audit.

Conditional status is not approval by default.

### 5.3 Prohibited candidates

Outcome facts, future observations, RFC-012 evidence, enrichment, outcome
availability, provenance, capture mode, collection identities, dataset
locations, absolute chronology proxies, completed-lifecycle counts, explicit
availability flags, raw candidate identifiers, Replay internals, and RFC-011
outputs remain outside the predictive surface.

### 5.4 Completeness statement

This audit covers:

- every field exposed by the current immutable `DecisionContext`;
- every one of the 72 outputs in the repository's existing default feature
  registry;
- the earlier-round deterministic-state authorization class in RQ-003; and
- the explicit prohibited categories named by RQ-003 and the Discovery
  Sessions.

No unlisted derived or historical feature is approved. A new concrete feature
would be feature engineering and requires a subsequent reviewed audit before
use.

## 6. Phase 1 disposition

The Decision-Time Feature Audit is complete as an inventory and boundary
classification. It authorizes no implementation and no outcome evaluation.

Before a later RQ-003 phase may evaluate any candidate set, that phase must
select only audited eligible candidates, resolve every conditional requirement,
record the exact immutable input schema, and revalidate that the selected
decision snapshot precedes all outcome evidence.
