# RFC-008 Implementation Plan

Status: **Approved for paper-only implementation; collection not authorized**

## 1. Frozen proposed design inputs

Implementation, if separately authorized, must consume the approval artifacts
without reinterpretation:

- candidate: `highest_reward_top4_v1` version `1.0.0`;
- candidate configuration SHA-256:
  `e60722e845d6364c41d28ebc7d1641f8c8726766f87bdb838f3822decf50a372`;
- trigger: first complete 25-square snapshot at or below 30.0 seconds
  (`slots_remaining <= 75`);
- sizing: four squares, equal allocation, 50,000 lamports;
- comparators: frozen random top-four, least-crowded/RFC-007 alias, and
  no-deploy;
- minimum: 600 independent primary-analyzable rounds;
- caps: 632 started rounds or 14 calendar days; and
- primary outcome provenance: directly and durably observed finalized
  outcomes only.

The candidate's ranking is descending `reward_raw`, then ascending square
index. Missing or invalid inputs cause explicit round abstention; no partial
selection or later snapshot substitution is allowed.

## 2. Current-system findings

The running observer reads the current board, treasury, and current round
account at confirmed commitment and appends one JSONL snapshot. It emits a
round-transition event only after observing the new round.

The RFC-007 collector:

- tails observer JSONL through durable byte/line cursors;
- creates one paper decision for every complete observation;
- supports one configured strategy per collector;
- consumes explicit finalized outcomes;
- refuses to infer a winner from time or transition alone;
- stores paper accounting separately from wallet-realized economics; and
- has no signer, transaction submission, or claim path.

The current outcome path does not durably enqueue every prior round for later
finalized resolution. RFC-007 therefore required post-hoc recovery for 13 of
14 Gate B rounds.

No change to the running observer PID `48404`, caffeinate PID `48405`, or
collector PID `78317` is required or permitted for RFC-008 design.

## 3. Smallest implementation sequence

### Phase 1 — Protocol types and marker

Add an RFC-008 configuration and immutable marker containing:

- preregistration hash;
- candidate and baseline definitions;
- candidate artifact hash;
- training/holdout boundary;
- random seed;
- decision trigger;
- round target and stopping rule;
- accounting assumptions; and
- source identities.

Validation must fail closed on any hash or configuration drift.

The marker must include the approval-manifest hash, candidate configuration
hash, random definition and seed material, 600/632/14-day stopping rule, and
the exact pre-holdout boundary. It may be created only after every approval
checklist item is resolved.

### Phase 2 — One-decision-per-round strategy matrix

Add a round decision builder that:

- selects the first complete snapshot at or below the frozen time threshold;
- evaluates every locked arm against the same snapshot;
- creates deterministic IDs keyed by experiment, round, and arm;
- prevents a second decision snapshot for the round; and
- records excluded rounds explicitly.

The candidate arm must sort all 25 squares by `reward_raw` descending and
square index ascending. The random arm must hash the literal material
`rfc008-random-top4-v1-seed-20260725:round_id:square_index` and order digests
bytewise ascending, then square index. Alias tests must prove that
`existing_least_crowded`, `least_miner_count`, and `lowest_miner_share`
produce the same ordering.

Do not retrofit this into the running RFC-007 ledger.

### Phase 3 — Durable outcome resolver

Create a separate process or library entry point with its own writer lease and
versioned store.

Required state machine:

`pending → resolving → finalized`

with terminal alternatives:

`conflicted`, `quarantined`, and `failed`.

Persist the pending-round queue before any network attempt. Resume unresolved
rounds after restart. Poll finalized state with bounded exponential backoff.
Store response hashes and provenance; never store RPC credentials.

The preferred architecture leaves the observer unchanged. The RFC-008
collector or a transition adapter records a durable transition event, and the
resolver asynchronously acquires the prior round outcome.

### Phase 4 — Round-level paper accounting

Apply the existing RFC-005/RFC-007 price-taking calculation to each strategy
arm. Store reconstructed paper accounting and configured fee assumptions with
explicit provenance.

The no-deploy arm records zero deployment, return, and fees.

### Phase 5 — Optional realized-accounting schema

Prepare, but do not activate, records for:

- transaction signature and fee payer;
- deployment debit and returned SOL;
- base and priority fees;
- failed-transaction costs;
- pre/post wallet SOL balances;
- pre/post ORE balances;
- claim signature, timing, and fee;
- base ORE and Motherlode ORE; and
- reconciliation completeness.

Collection of these fields requires separate transaction and live-safety
authorization. Missing realized values remain unavailable, never assumed.

### Phase 6 — Analysis and audit tooling

Build a derived one-row-per-round dataset and deterministic analysis command.
The command must verify the marker, source hashes, sample count, outcome
durability, strategy completeness, missingness, and provenance before running
the locked tests in RFC-008.

## 4. Proposed schema additions

Use a new collection schema version and new versioned database. Proposed
tables:

- `experiment_markers`
- `experiment_rounds`
- `round_decision_snapshots`
- `round_strategy_decisions`
- `outcome_acquisition_queue`
- `outcome_acquisition_attempts`
- `durable_final_outcomes`
- `round_paper_accounting`
- `participant_transactions`
- `participant_fee_observations`
- `participant_wallet_observations`
- `participant_returns`
- `participant_claims`
- `round_reconciliation`

Uniqueness requirements:

- one active marker per experiment ID;
- one eligibility record per experiment and round;
- one decision snapshot per experiment and round;
- one decision per experiment, round, and strategy arm;
- one accepted finalized outcome per round and version;
- one accounting record per experiment, round, and arm; and
- no terminal reconciliation without a complete provenance chain.

Migrations must be additive, idempotent, rollback-tested, and must never target
the live RFC-007 ledger.

## 5. Required tests

1. Exact one-decision snapshot per round.
2. Identical input snapshot across all strategy arms.
3. Deterministic random baseline.
4. RFC-007 reference alias matches least-crowded without double counting.
5. Candidate artifact and configuration hash enforcement.
6. Marker and holdout-boundary immutability.
7. No future or finalized outcome fields enter decisions.
8. Pending outcome persists before resolution.
9. Resolver restart resumes every pending round.
10. Transition cannot silently drop the prior round.
11. Finalized commitment, owner, PDA, round, and decoder validation.
12. Provider disagreement and correction quarantine.
13. Missing outcome and 24-hour quarantine behavior.
14. More-than-5% missingness failure.
15. Price-taking accounting and no-deploy control.
16. Configured versus directly observed fee provenance.
17. Missing base ORE remains unavailable.
18. One-row-per-round derived dataset.
19. Exact McNemar and paired bootstrap reproducibility.
20. Stopping without performance peeking.
21. Strict JSON and non-finite rejection.
22. No signer, submission, claim, or live-action reachability.
23. Observer and RFC-007 process noninterference.
24. Candidate reward ordering and ascending-index tie break.
25. Candidate abstention on missing, negative, non-integer, or non-finite
    reward input.
26. All 25 squares are ranked before the first four are selected.
27. Frozen candidate configuration hash and approval-manifest hash.
28. Exact 600 analyzable, 632 started, and 14-day stopping boundaries.
29. Recovered outcomes never increment the primary-analyzable count.
30. Decision-table classification is mutually exclusive and exhaustive.

## 6. Pre-collection checkpoint

Before any RFC-008 collection is authorized:

1. resolve every human approval listed in RFC-008 Section 18;
2. commit implementation and tests;
3. run the complete test suite;
4. complete a fixture and restart burn-in;
5. independently reproduce the committed paired power calculation;
6. verify the frozen candidate and configuration artifacts;
7. produce and hash the immutable marker;
8. confirm new output paths and writer lease;
9. confirm the existing observer and collector remain untouched; and
10. obtain separate explicit authorization to start collection.

No RFC-008 collection, RPC polling, wallet access, or live action begins in
this implementation-plan phase.
