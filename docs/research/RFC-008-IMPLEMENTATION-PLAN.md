# RFC-008 Implementation Plan

Status: **Design only; implementation and collection not authorized**

## 1. Current-system findings

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

## 2. Smallest implementation sequence

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

### Phase 2 — One-decision-per-round strategy matrix

Add a round decision builder that:

- selects the first complete snapshot at or below the frozen time threshold;
- evaluates every locked arm against the same snapshot;
- creates deterministic IDs keyed by experiment, round, and arm;
- prevents a second decision snapshot for the round; and
- records excluded rounds explicitly.

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

## 3. Proposed schema additions

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

## 4. Required tests

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

## 5. Pre-collection checkpoint

Before any RFC-008 collection is authorized:

1. resolve every human approval listed in RFC-008 Section 18;
2. commit implementation and tests;
3. run the complete test suite;
4. complete a fixture and restart burn-in;
5. calculate paired power using pre-holdout data;
6. freeze candidate and configuration artifacts;
7. produce and hash the immutable marker;
8. confirm new output paths and writer lease;
9. confirm the existing observer and collector remain untouched; and
10. obtain separate explicit authorization to start collection.

No RFC-008 collection, RPC polling, wallet access, or live action begins in
this implementation-plan phase.
