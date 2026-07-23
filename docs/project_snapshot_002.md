# ORE Miner V3 — Project Snapshot 002

## Current Status

ORE Miner V3 has completed its first validated read-only data collection milestone.

The project currently has:

- A standalone V3 repository
- A committed security and secret-handling policy
- A read-only Solana RPC client
- ORE Board account decoding
- ORE Treasury account decoding
- Current Round PDA derivation
- Active and finalized Round account decoding
- A finalized-round inspection tool
- An append-only immutable JSONL snapshot collector

No wallet, transaction signing, or live mining capability has been implemented.

## Verified Protocol State

The Observer currently reads:

### Board
- round_id
- start_slot
- end_slot
- production_cost_ema

### Treasury
- live accumulating Motherlode

The Treasury Motherlode was verified against ore.com.

Observed examples:
- 201.8 ORE
- 203.6 ORE

### Round
- 25 deployed SOL values
- 25 miner counts
- 25 mass values
- slot hash
- expiration slot
- round-specific Motherlode payout
- 25-element reward array
- total_vaulted
- total_winnings
- total_miners
- top_miner
- derived entropy

## Important Findings

### Motherlode

The accumulating Motherlode is stored in:

Treasury.motherlode

The field:

Round.motherlode

is separate and is normally zero unless that specific finalized round receives the Motherlode payout.

### Mass

The 25-element mass array remains zero in both active and finalized rounds.

Current treatment:

- Preserve as raw protocol state
- Do not use as a strategy feature
- Continue monitoring in case future protocol behavior changes

### Solo Rewards

Solo rewards must not be inferred from:

winning_square_miner_count == 1

The finalized-round state exposes separate solo/split reward behavior through top_miner.

### Reward Array

The 25-element reward array is not currently interpreted as a per-square reward mapping.

A finalized round showed:

- reward index 0 = 1 ORE
- winning square = 23

Therefore the array must be preserved without assigning unsupported semantics.

## Finalized Round Validation

Round 342054 was successfully inspected after settlement.

Observed:

- Winning square: 23
- Winning-square miners: 144
- Winning-square deployed: approximately 0.453312733 SOL
- Total deployed: approximately 10.792649615 SOL
- Total winnings: approximately 9.212349163 SOL
- Total vaulted: approximately 1.023594351 SOL
- Round Motherlode payout: 0 ORE
- Slot hash populated
- Entropy populated
- top_miner = SpLiT11111111111111111111111111111111111112
- All mass values remained zero

## Snapshot Logger

The immutable snapshot logger is implemented.

Command:

python -m orev3.observer.collect

Default interval:

0.8 seconds

Output:

data/raw/observer_YYYY-MM-DD.jsonl

Files rotate by UTC date.

Raw data is intentionally ignored by Git.

Each snapshot includes:

- schema_version
- observed_at_utc
- rpc_slot
- Board state
- Treasury state
- full current Round state

A one-shot snapshot was successfully validated.

Example validated snapshot:

- schema_version: 1
- round_id: 342063
- rpc_slot: 434649187
- Treasury Motherlode: 203.6 ORE
- 25 deployed entries
- 25 miner-count entries

## Current Live Activity

The continuous collector is now running for at least one hour.

Purpose:

- Capture multiple complete round transitions
- Measure snapshot frequency
- Detect gaps
- Detect duplicate slots
- Validate round ID and PDA transitions
- Check for malformed or partial snapshots
- Confirm data integrity across active-round transitions

## Alignment With Original Plan

The project remains aligned with the original architecture:

Observer
↓
Historical Dataset
↓
Replay Engine
↓
Strategy Lab
↓
Decision Engine
↓
Portfolio Simulator
↓
Paper Miner
↓
Live Miner
↓
Adaptive Strategy Layer

Current position:

Observer — core decoding validated, continuous collection in progress

Historical Dataset — not started

Replay Engine — not started

Strategy Lab — not started

Decision Engine — not started

Portfolio Simulator — not started

Paper Miner — not started

Live Miner — not started

Adaptive Strategy Layer — not started

## Next Step

After at least one hour of continuous collection:

1. Stop the collector with Control+C.
2. Analyze the JSONL dataset for:
   - round transitions
   - gaps
   - duplicate slots
   - polling frequency
   - collector errors
   - malformed snapshots
   - partial-state snapshots
3. Confirm previous finalized rounds remain inspectable.
4. If the dataset passes validation, begin the Historical Dataset / round lifecycle assembler.

